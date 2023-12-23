from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey, Float
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(Integer, index=True, unique=True)
    password = Column(String, index=True)
    name = Column(String, index=True)
    surname = Column(String, index=True)
    balance = Column(Float, index=True)
    operations = relationship('Operation', back_populates='user')


class Operation(Base):
    __tablename__ = 'operations'
    id = Column(Integer, primary_key=True, index=True)
    value = Column(Float, index=True)
    type = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User', back_populates='operations')