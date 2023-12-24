from datetime import datetime
from typing import List

import sqlalchemy
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.exc import IntegrityError

import schemas
from database import get_db
from sqlalchemy.orm import Session
from crud import (
    create_user, get_users, get_user, update_user_by_phone, delete_user,
    create_operation, get_operations, get_operations_by_user, get_operations_by_date,
    update_operation, delete_operation, get_user_by_phone, delete_operation_by_params
)

router_websocket = APIRouter()
router_users = APIRouter(prefix='/user', tags=['User'])
router_operations = APIRouter(prefix='/operation', tags=['Operation'])


# WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    async def send_global_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


async def notify_clients(message: str):
    for connection in manager.active_connections:
        await connection.send_text(message)


@router_websocket.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(websocket)
    await manager.broadcast(f"User #{user_id} is now online.")
    try:
        while True:
            data = await websocket.receive_text()
            # await manager.send_personal_message(f"You wrote: {data}", websocket)
            # await manager.broadcast(f"Client #{user_id} says: {data}")
            await manager.send_global_message(data, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"User #{user_id} is now offline.")


# user
@router_users.post("/", response_model=schemas.User)
async def create_user_route(category_data: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        user = await create_user(db, category_data)
    except ValueError:
        raise HTTPException(status_code=406, detail="Wrong input type")
    except IntegrityError:
        raise HTTPException(status_code=406, detail="Input is not UNIQUE")
    except Exception:
        raise HTTPException(status_code=406, detail="Wrong phone number length")
    else:
        await notify_clients(f"Welcome new user : {user.name} {user.surname}")
        return user


@router_users.get("/", response_model=List[schemas.User])
async def read_users(db: Session = Depends(get_db)):
    users = await get_users(db)
    return users


@router_users.get("/id/{user_id}", response_model=schemas.User)
async def read_user(user_id: int, db: Session = Depends(get_db)):
    user = await get_user(db, user_id)
    if user:
        return user
    else:
        raise HTTPException(status_code=404, detail="User not found")


@router_users.get("/phone/{phone}", response_model=schemas.User)
async def read_user_by_phone(phone: int, password: str, db: Session = Depends(get_db)):
    user = await get_user_by_phone(db, phone)
    if user:
        if user.password == password:
            return user
        else:
            raise HTTPException(status_code=403, detail="Wrong password")
    else:
        raise HTTPException(status_code=404, detail="User not found")


@router_users.put("/phone/", response_model=schemas.User)
async def update_user_by_phone_route(phone: int, user_data: schemas.User, db: Session = Depends(get_db)):
    try:
        updated_user = await update_user_by_phone(db, phone, user_data)
    except SyntaxError:
        raise HTTPException(status_code=406, detail="Wrong phone number length")
    except Exception:
        raise HTTPException(status_code=404, detail="User not found")
    else:
        await notify_clients(f"User updated: #{updated_user.id}")
        return updated_user


@router_users.delete("/{user_id}")
async def delete_user_route(user_id: int, db: Session = Depends(get_db)):
    ops = await get_operations_by_user(db, user_id)
    for op in ops:
        await delete_operation(db, op.id)
    deleted = await delete_user(db, user_id)
    if deleted:
        await notify_clients(f"User deleted: #{user_id}")
        return {"message": "User deleted"}
    else:
        raise HTTPException(status_code=404, detail="User not found")


# operations
@router_operations.post("/", response_model=schemas.Operation)
async def create_operation_route(schema: schemas.OperationCreate, db: Session = Depends(get_db)):
    try:
        operation = await create_operation(db, schema)
    except ValueError:
        raise HTTPException(status_code=406, detail="Wrong type(only wage or payment)")
    except Exception:
        raise HTTPException(status_code=404, detail="User not found")
    await notify_clients(f"User #{operation.user_id} added new operation")
    return operation


@router_operations.get("/", response_model=List[schemas.Operation])
async def read_operations(db: Session = Depends(get_db)):
    operations = await get_operations(db)
    return operations


@router_operations.get("/user/{user_id}", response_model=List[schemas.Operation])
async def read_operations_by_user(user_id: int, db: Session = Depends(get_db)):
    operations = await get_operations_by_user(db, user_id)
    if operations:
        return operations
    raise HTTPException(status_code=404, detail="Operations not found")


@router_operations.get("/date/{user_id}", response_model=List[schemas.Operation])
async def read_operations_by_date(date: datetime, user_id: int, db: Session = Depends(get_db)):
    operations = await get_operations_by_date(db, user_id, date)
    if operations:
        return operations
    else:
        raise HTTPException(status_code=404, detail="Operations not found")


@router_operations.patch("/{oper_id}")
async def update_operation_route(oper_id: int, schema: schemas.OperationUpdate, db: Session = Depends(get_db)):
    try:
        updated_oper = await update_operation(db, oper_id, schema)
    except IndexError:
        raise HTTPException(status_code=404, detail="Operation not found")
    except ValueError:
        raise HTTPException(status_code=406, detail="Wrong type(only wage or payment)")
    except Exception:
        raise HTTPException(status_code=404, detail="User not found")
    await notify_clients(f"Operation updated: #{updated_oper.id}")
    return updated_oper


@router_operations.delete("/{oper_id}")
async def delete_operation_route(oper_id: int, db: Session = Depends(get_db)):
    try:
        deleted = await delete_operation(db, oper_id)
    except ValueError:
        raise HTTPException(status_code=406, detail="Wrong type(only wage or payment)")
    if deleted:
        await notify_clients(f"Operation deleted: #{oper_id}")
        return {"message": "Operation deleted"}
    else:
        raise HTTPException(status_code=404, detail="Operation not found")


@router_operations.delete("/params/{user_id}")
async def delete_operation_by_params_route(user_id: int, value: float, type: str, created_at: datetime, db: Session = Depends(get_db)):
    try:
        deleted = await delete_operation_by_params(db, value, type, created_at, user_id)
    except ValueError:
        raise HTTPException(status_code=406, detail="Wrong type(only wage or payment)")
    if deleted:
        await notify_clients(f"Deleted operation of user #{user_id}")
        return {"message": "Operation deleted"}
    else:
        raise HTTPException(status_code=404, detail="Operation not found")