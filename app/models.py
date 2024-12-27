import uuid
from pydantic import (
    EmailStr,
    BaseModel,
    StringConstraints,
    model_serializer,
)
from sqlmodel import Field, SQLModel
from enum import Enum
from datetime import datetime
from typing import List
from typing_extensions import Annotated
from pydantic.networks import IPvAnyAddress


SUBSCRIPTION_NAME_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,8}$"
)

OPTIONALLY_FULLY_QUALIFIED_DOMAIN_NAME_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}\.?$"
)


class UserRoles(Enum):
    SUPERUSER = "superuser"
    ADMIN = "admin"
    USER = "user"


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    full_name: str | None = Field(default=None, max_length=255)
    role: UserRoles = Field(default=UserRoles.USER)
    ssh_username: str | None = Field(default=None, max_length=33)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=40)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=40)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)
    ssh_username: str | None = Field(default=None, max_length=33)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)


class UserAction(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    action: str
    server: str | None = None
    timestamp: datetime
    status: str


class DomainName(BaseModel):
    domain: Annotated[
        str,
        StringConstraints(
            min_length=3,
            max_length=253,
            pattern=OPTIONALLY_FULLY_QUALIFIED_DOMAIN_NAME_PATTERN,
        ),
    ]

    model_config = {"json_schema_extra": {"examples": ["example.com."]}}

    @model_serializer(mode="wrap")
    def ser_model(self, _handler):
        return self.domain


class IPv4Address(BaseModel):
    ip: IPvAnyAddress

    def __str__(self) -> str:
        return str(self.ip)

    @model_serializer(mode="wrap")
    def ser_model(self, _handler):
        return str(self.ip)

    model_config = {"json_schema_extra": {"examples": ["IP_PLACEHOLDER"]}}


class DomainARecordResponse(BaseModel):
    domain: DomainName
    records: List[IPv4Address]


class PtrRecordResponse(BaseModel):
    ip: IPv4Address
    records: List[DomainName]


class DomainMxRecordResponse(BaseModel):
    domain: DomainName
    records: List[DomainName]


class DomainNsRecordResponse(BaseModel):
    domain: DomainName
    records: List[DomainName]


class SubscriptionName(BaseModel):
    domain: Annotated[
        str,
        StringConstraints(
            min_length=3,
            max_length=253,
            pattern=SUBSCRIPTION_NAME_PATTERN,
        ),
    ]

    model_config = {"json_schema_extra": {"examples": ["v-12312.webspace"]}}

    @model_serializer(mode="wrap")
    def ser_model(self, _handler):
        return self.domain
