import uuid
from pydantic import EmailStr, BaseModel, StringConstraints, model_serializer, RootModel
from sqlmodel import Field, SQLModel, Relationship, AutoString
from enum import Enum
from typing import List
from typing_extensions import Annotated
from pydantic.networks import IPvAnyAddress
from ipaddress import ip_address

SUBSCRIPTION_NAME_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,8}$"
)

OPTIONALLY_FULLY_QUALIFIED_DOMAIN_NAME_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}\.?$"
)

LINUX_USERNAME_PATTERN = r"^[a-z_]([a-z0-9_-]{0,31}|[a-z0-9_-]{0,30}\$)$"


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


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    full_name: str | None = Field(default=None, max_length=255)
    role: UserRoles = Field(default=UserRoles.USER)
    ssh_username: str | None = Field(default=None, max_length=32)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str


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


class IPv4Address(RootModel):
    root: IPvAnyAddress

    def __init__(self, root: str):
        super().__init__(root=ip_address(root))

    def __str__(self) -> str:
        return str(self.root)

    @model_serializer(mode="wrap")
    def ser_model(self, _handler):
        return str(self.root)

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


class UserActionType(str, Enum):
    GET_ZONE_MASTER = "GET_ZONE_MASTER"
    DELETE_ZONE_MASTER = "DELETE_ZONE_MASTER"
    SET_ZONE_MASTER = "SET_ZONE_MASTER"
    GENERATE_LOGIN_LINK = "GENERATE_LOGIN_LINK"


class UsersActivityLog(SQLModel, table=True):
    __tablename__ = "users_activity_log"  # type: ignore

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    action: UserActionType
    server: str
    timestamp: str

    # Relationships to action-specific logs
    dns_zone_delete_logs: list["DeleteZonemasterLog"] = Relationship(
        back_populates="user_action"
    )
    dns_set_zone_master_logs: list["SetZoneMasterLog"] = Relationship(
        back_populates="user_action"
    )
    dns_get_zone_master_logs: list["GetZoneMasterLog"] = Relationship(
        back_populates="user_action"
    )


class UserActionLogBase(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_action_id: uuid.UUID = Field(foreign_key="users_activity_log.id")


class DeleteZonemasterLog(UserActionLogBase, table=True):
    __tablename__ = "zone_master_delete_log"  # type: ignore

    current_zone_master: DomainName = Field(sa_type=AutoString)
    user_action: "UsersActivityLog" = Relationship(
        back_populates="dns_zone_delete_logs"
    )


class SetZoneMasterLog(UserActionLogBase, table=True):
    __tablename__ = "zone_master_set_log"  # type: ignore

    current_zone_master: DomainName | None = Field(sa_type=AutoString)
    target_zone_master: DomainName = Field(sa_type=AutoString)
    domain: DomainName = Field(sa_type=AutoString)
    user_action: "UsersActivityLog" = Relationship(
        back_populates="dns_set_zone_master_logs"
    )


class GetZoneMasterLog(UserActionLogBase, table=True):
    __tablename__ = "zone_master_get_log"  # type: ignore

    domain: SubscriptionName = Field(sa_type=AutoString)
    user_action: "UsersActivityLog" = Relationship(
        back_populates="dns_get_zone_master_logs"
    )
