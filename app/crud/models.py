import uuid
from sqlalchemy import Column, ForeignKey, String, UUID, Integer , Enum
from sqlalchemy.orm import relationship, DeclarativeBase

from app.schemas import UserRoles

class Base(DeclarativeBase):
    pass


# Shared properties
class UserBase(Base):
    __abstract__ = True

    email = Column(String(255), unique=True, index=True, nullable=False)
    is_active = Column(String, default=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(Enum, default=UserRoles.USER, nullable=False)
    ssh_username = Column(String(32), nullable=True)


# Database model, database table inferred from class name
class User(UserBase):
    __tablename__ = UserRoles.USER

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hashed_password = Column(String, nullable=False)


# Properties to receive via API on creation
class UserCreate:
    email = Column(String(255), nullable=False)
    password = Column(String(40), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(String, default=True, nullable=False)
    role = Column(Enum, default=UserRoles.USER, nullable=False)
    ssh_username = Column(String(32), nullable=True)


class UserRegister:
    email = Column(String(255), nullable=False)
    password = Column(String(40), nullable=False)
    full_name = Column(String(255), nullable=True)


# Properties to receive via API on update, all are optional
class UserUpdate:
    email = Column(String(255), nullable=True)
    password = Column(String(40), nullable=True)
    full_name = Column(String(255), nullable=True)
    is_active = Column(String, default=True, nullable=False)
    role = Column(Enum, default=UserRoles.USER, nullable=False)
    ssh_username = Column(String(32), nullable=True)


class UserUpdateMe:
    full_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    ssh_username = Column(String(33), nullable=True)


class UserPublic:
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False)
    is_active = Column(String, default=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(Enum, default=UserRoles.USER, nullable=False)
    ssh_username = Column(String(32), nullable=True)


class UsersPublic:
    data = Column(String)  # JSON representation of list[UserPublic]
    count = Column(Integer)
