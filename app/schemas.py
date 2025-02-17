import uuid
from pydantic import (
    EmailStr,
    BaseModel,
    StringConstraints,
    model_serializer,
    field_validator,
)
from sqlmodel import Field, SQLModel
from enum import Enum
from typing import List
from typing_extensions import Annotated
from ipaddress import ip_address
from sqlalchemy import Column, ForeignKey, String, UUID
from sqlalchemy.orm import relationship, DeclarativeBase


from app.host_lists import PLESK_SERVER_LIST

SUBSCRIPTION_NAME_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,8}$"
)

OPTIONALLY_FULLY_QUALIFIED_DOMAIN_NAME_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}\.?$"
)

LINUX_USERNAME_PATTERN = r"^[a-z_]([a-z0-9_-]{0,31}|[a-z0-9_-]{0,30}\$)$"


class UserRoles(str, Enum):
    SUPERUSER = "superuser"
    ADMIN = "admin"
    USER = "user"
    
    @classmethod
    def _missing_(cls, value) -> str|None:
        value = value.lower() # type: ignore
        for member in cls:
            if member.lower() == value:
                return member
        return None


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class UserBase(BaseModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    full_name: str | None = Field(default=None, max_length=255)
    role: UserRoles = Field(default=UserRoles.USER)
    ssh_username: str | None = Field(default=None, max_length=32)


class User(UserBase):
    hashed_password: str


class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=40)


class UserUpdateMe(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)
    ssh_username: str | None = Field(default=None, max_length=33)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=40)


class UserRegister(BaseModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    full_name: str | None = Field(default=None, max_length=255)


class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(BaseModel):
    data: list[UserPublic]
    count: int


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# Generic message
class Message(SQLModel):
    message: str


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)


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

    def __str__(self):
        return self.domain


class PleskServerDomain(BaseModel):
    domain: Annotated[
        str,
        StringConstraints(
            min_length=3,
            max_length=253,
            pattern=OPTIONALLY_FULLY_QUALIFIED_DOMAIN_NAME_PATTERN,
        ),
    ]
example.com

    @field_validator("domain")
    def validate_domain(cls, v):
        if v not in PLESK_SERVER_LIST:
            raise ValueError(f"Domain '{v}' is not in the list of Plesk servers.")
        return v

    def __str__(self):
        return self.domain


class IPv4Address(BaseModel):
    ip: str

    def __init__(self, ip: str):
        super().__init__(ip=str(ip_address(ip)))

    def __str__(self) -> str:
        return self.ip

    @model_serializer
    def serialize(self) -> str:
        return self.ip

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

    model_config = {"json_schema_extra": {"examples": ["v12312.webspace"]}}

    @model_serializer(mode="wrap")
    def ser_model(self, _handler):
        return self.domain


class UserActionType(str, Enum):
    GET_ZONE_MASTER = "GET_ZONE_MASTER"
    DELETE_ZONE_MASTER = "DELETE_ZONE_MASTER"
    SET_ZONE_MASTER = "SET_ZONE_MASTER"
    GENERATE_LOGIN_LINK = "GENERATE_LOGIN_LINK"


class Base(DeclarativeBase):
    pass


