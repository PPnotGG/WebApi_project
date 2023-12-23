from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


# User
class UserBase(BaseModel):
    phone: int
    name: str
    surname: str
    balance: float = 0
    password: str = Field(min_length=8)


class UserCreate(UserBase):
    pass


class User(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


# Operation
class OperationBase(BaseModel):
    value: float = Field(ge=0)
    type: str
    user_id: int
    created_at: datetime


class OperationCreate(OperationBase):
    pass


class OperationUpdate(BaseModel):
    value: float = Field(ge=0)
    type: str
    created_at: datetime


class Operation(OperationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int