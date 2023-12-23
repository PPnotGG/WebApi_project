from datetime import datetime

from sqlalchemy.orm import Session

import schemas
from models import User, Operation


# Category
async def create_user(db: Session, schema: schemas.UserCreate):
    db_user = User(**schema.model_dump())
    if len(str(db_user.phone)) < 10:
        raise Exception()
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


async def get_users(db: Session):
    return db.query(User).all()


async def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id==user_id).first()


async def get_user_by_phone(db: Session, phone: int):
    return db.query(User).filter(User.phone==phone).first()


async def update_user_by_phone(db: Session, phone: int, schema: schemas.UserBase):
    db_user = db.query(User).filter(User.phone==phone).first()
    if db_user:
        if len(str(schema.phone)) < 10:
            raise SyntaxError
        db_user.phone = schema.phone
        db_user.name = schema.name
        db_user.surname = schema.surname
        db_user.password = schema.password
        db_user.balance = schema.balance
        db.commit()
        db.refresh(db_user)
        return db_user
    else:
        raise Exception


async def update_users_balance(db: Session, user_id: int, type: str, value: float):
    user = await get_user(db, user_id)
    if type == "payment":
        user.balance -= value
    elif type == "wage":
        user.balance += value
    else:
        raise ValueError
    db.commit()
    db.refresh(user)


async def rollback_users_balance(db: Session, user_id: int, type: str, value: float):
    user = await get_user(db, user_id)
    if type == "wage":
        user.balance -= value
    elif type == "payment":
        user.balance += value
    else:
        raise ValueError
    db.commit()
    db.refresh(user)


async def delete_user(db: Session, user_id: int):
    db_user = db.query(User).filter(User.id==user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
        return True
    return False


# Item
async def create_operation(db: Session, schema: schemas.OperationCreate):
    if get_user(db, schema.user_id):
        db_oper = Operation(**schema.model_dump())
        await update_users_balance(db, schema.user_id, db_oper.type, db_oper.value)
        db.add(db_oper)
        db.commit()
        db.refresh(db_oper)
        return db_oper
    else:
        raise Exception


async def get_operations(db: Session):
    return db.query(Operation).all()


async def get_operations_by_user(db: Session, user_id: int):
    return db.query(Operation).filter(Operation.user_id==user_id).all()


async def get_operations_by_date(db: Session, user_id: int, date: datetime):
    return db.query(Operation).filter(Operation.user_id==user_id, Operation.created_at==date).all()


async def update_operation(db: Session, oper_id: int, schema: schemas.OperationUpdate):
    db_oper = db.query(Operation).filter(Operation.id==oper_id).first()
    if db_oper:
        await rollback_users_balance(db, db_oper.user_id, db_oper.type, db_oper.value)
        db_oper.value = schema.value
        db_oper.type = schema.type
        db_oper.created_at = schema.created_at
        await update_users_balance(db, db_oper.user_id, db_oper.type, db_oper.value)
        db.commit()
        db.refresh(db_oper)
        return db_oper
    else:
        raise IndexError


async def delete_operation(db: Session, oper_id: int):
    db_oper = db.query(Operation).filter(Operation.id==oper_id).first()
    if db_oper:
        await rollback_users_balance(db, db_oper.user_id, db_oper.type, db_oper.value)
        db.delete(db_oper)
        db.commit()
        return True
    return False


async def delete_operation_by_params(db: Session, value: float, type: str, created_at: datetime, user_id: int):
    db_oper = db.query(Operation).filter(Operation.value==value, Operation.type==type, Operation.created_at==created_at, Operation.user_id==user_id).first()
    if db_oper:
        await rollback_users_balance(db, db_oper.user_id, db_oper.type, db_oper.value)
        db.delete(db_oper)
        db.commit()
        return True
    return False
