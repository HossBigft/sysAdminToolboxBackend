import uuid

from pydantic import (
    EmailStr,
    BaseModel,
    StringConstraints,
    model_serializer,
    field_validator,
    ConfigDict,
    Field,
    model_validator,
    RootModel,
)
from pydantic.json_schema import SkipJsonSchema
from enum import Enum
from typing import List, Literal, Any
from typing_extensions import Annotated
from datetime import datetime
from pydantic.networks import IPvAnyAddress


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
    def _missing_(cls, value) -> str | None:
        value = value.lower()  # type: ignore
        for member in cls:
            if member.lower() == value:
                return member
        return None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None


class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: EmailStr = Field(max_length=255)
    is_active: bool = True
    full_name: str | None = Field(default=None, max_length=255)
    role: UserRoles = Field(default=UserRoles.USER)
    ssh_username: str | None = Field(default=None, max_length=32)


class UserUpdateMePassword(UserBase):
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


class UpdatePassword(BaseModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


class Message(BaseModel):
    message: str


class NewPassword(BaseModel):
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

    @model_validator(mode="before")
    @classmethod
    def validate_ip_input(cls, data: Any) -> Any:
        """Convert string inputs to proper dict structure."""
        if isinstance(data, str):
            return {"domain": data}
        return data

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

    @model_validator(mode="before")
    @classmethod
    def validate_ip_input(cls, data: Any) -> Any:
        """Convert string inputs to proper dict structure."""
        if isinstance(data, str):
            return {"domain": data}
        return data

    def __str__(self):
        return self.domain


class IPv4Address(BaseModel):
    ip: IPvAnyAddress

    def __str__(self) -> str:
        return str(self.ip)

    @model_validator(mode="before")
    @classmethod
    def validate_ip_input(cls, data: Any) -> Any:
        """Convert string inputs to proper dict structure."""
        if isinstance(data, str):
            return {"ip": data}
        return data

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

    model_config = {"json_schema_extra": {"examples": ["v12312.webspace"]}}

    @model_serializer(mode="wrap")
    def ser_model(self, _handler):
        return self.domain


class UserActionType(str, Enum):
    GET_ZONE_MASTER = "GET_ZONE_MASTER"
    DELETE_ZONE_MASTER = "DELETE_ZONE_MASTER"
    SET_ZONE_MASTER = "SET_ZONE_MASTER"
    GET_SUBSCRIPTION_LOGIN_LINK = "GET_SUBSCRIPTION_LOGIN_LINK"


class UserLogBaseSchema(BaseModel):
    ip: IPv4Address
    timestamp: datetime


class DeleteZonemasterLogSchema(UserLogBaseSchema):
    domain: DomainName
    current_zone_master: str
    log_type: Literal[UserActionType.DELETE_ZONE_MASTER]


class SetZoneMasterLogSchema(UserLogBaseSchema):
    domain: DomainName
    target_zone_master: PleskServerDomain
    current_zone_master: PleskServerDomain | None
    log_type: Literal[UserActionType.SET_ZONE_MASTER]


class GetZoneMasterLogSchema(UserLogBaseSchema):
    domain: DomainName
    log_type: Literal[UserActionType.GET_ZONE_MASTER]


class GetPleskLoginLinkLogSchema(UserLogBaseSchema):
    plesk_server: PleskServerDomain
    subscription_id: int
    log_type: Literal[UserActionType.GET_SUBSCRIPTION_LOGIN_LINK]


class UserLogPublic(UserPublic):
    email: SkipJsonSchema[EmailStr] = Field(exclude=True)
    is_active: SkipJsonSchema[bool] = Field(default=False, exclude=True)

    details: (
        DeleteZonemasterLogSchema
        | SetZoneMasterLogSchema
        | GetZoneMasterLogSchema
        | GetPleskLoginLinkLogSchema
    ) = Field(discriminator="log_type")


class LinuxUsername(RootModel):
    root: Annotated[
        str,
        StringConstraints(
            min_length=3,
            max_length=32,
            pattern=LINUX_USERNAME_PATTERN,
        ),
    ]

    @model_serializer(mode="wrap")
    def ser_model(self, _handler):
        return str(self.root)

    def __str__(self) -> str:
        return str(self.root)


class UserLogSearchSchema(BaseModel):
    user_id: uuid.UUID | None = None
    ip: IPv4Address | None = None
    timestamp: datetime | None = None
    log_type: UserActionType | None = None
    domain: DomainName | None = None
    plesk_server: PleskServerDomain | None = None
    subscription_id: int | None = None
    ssh_username: LinuxUsername | None = None
