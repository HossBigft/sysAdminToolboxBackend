import uuid
import json

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
from typing import (
    List,
    Literal,
    Any,
    Generic,
    Optional,
    TypeVar,
    TypedDict,
    Type,
)
from typing_extensions import Annotated
from datetime import datetime
from pydantic.networks import IPvAnyAddress
from app.core.config import settings
from pydantic.generics import GenericModel


SUBSCRIPTION_NAME_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,9}$"
)

OPTIONALLY_FULLY_QUALIFIED_DOMAIN_NAME_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}\.?$"
)

LINUX_USERNAME_PATTERN = r"^[a-z_]([a-z0-9_-]{0,31}|[a-z0-9_-]{0,30}\$)$"

PLESK_SERVER_LIST: list[str] = list(settings.PLESK_SERVERS.keys())
DNS_SERVER_LIST: list[str] = list(settings.DNS_SLAVE_SERVERS.keys())


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


ValidatedDomainName = Annotated[
    str,
    StringConstraints(
        min_length=3,
        max_length=253,
        pattern=OPTIONALLY_FULLY_QUALIFIED_DOMAIN_NAME_PATTERN,
    ),
]


class DomainName(BaseModel):
    name: ValidatedDomainName

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
        return self.name

    def __str__(self):
        return self.name


ValidatedPleskServerDomain = Annotated[
    str,
    StringConstraints(
        min_length=3,
        max_length=253,
        pattern=OPTIONALLY_FULLY_QUALIFIED_DOMAIN_NAME_PATTERN,
    ),
]


class PleskServerDomain(BaseModel):
    name: ValidatedPleskServerDomain
    model_config = {"json_schema_extra": {"examples": [PLESK_SERVER_LIST[0]]}}

    @field_validator("name")
    def validate_domain(cls, v):
        if v.endswith("."):
            v = v[:-1]
        if v not in PLESK_SERVER_LIST:
            raise ValueError(f"Domain '{v}' is not in the list of Plesk servers.")
        return v

    @model_validator(mode="before")
    @classmethod
    def validate_ip_input(cls, data: Any) -> Any:
        """Convert string inputs to proper dict structure."""
        if isinstance(data, str):
            return {"name": data}
        return data

    def __str__(self):
        return self.name


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

    model_config = {
        "json_schema_extra": {
            "examples": [settings.PLESK_SERVERS[PLESK_SERVER_LIST[0]]]
        }
    }


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
    name: Annotated[
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
        return self.name


class UserActionType(str, Enum):
    GET_ZONE_MASTER = "GET_ZONE_MASTER"
    DELETE_ZONE_MASTER = "DELETE_ZONE_MASTER"
    SET_ZONE_MASTER = "SET_ZONE_MASTER"
    GET_SUBSCRIPTION_LOGIN_LINK_BY_DOMAIN = "GET_SUBSCRIPTION_LOGIN_LINK"
    GET_TEST_MAIL_CREDENTIALS = "PLESK_MAIL_GET_TEST_MAIL"


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
    log_type: Literal[UserActionType.GET_SUBSCRIPTION_LOGIN_LINK_BY_DOMAIN]
    ssh_username: LinuxUsername


class UserLogPublic(UserPublic):
    email: SkipJsonSchema[EmailStr] = Field(exclude=True)
    is_active: SkipJsonSchema[bool] = Field(default=False, exclude=True)

    details: (
        DeleteZonemasterLogSchema
        | SetZoneMasterLogSchema
        | GetZoneMasterLogSchema
        | GetPleskLoginLinkLogSchema
    ) = Field(discriminator="log_type")


class UserActivityLogFilterSchema(BaseModel):
    ip: IPv4Address | None = None
    timestamp: datetime | None = None
    log_type: UserActionType | None = None
    domain: DomainName | None = None
    plesk_server: PleskServerDomain | None = None
    subscription_id: int | None = None
    ssh_username: LinuxUsername | None = None


class UserLogFilterSchema(UserActivityLogFilterSchema):
    user_id: uuid.UUID | None = None


class PaginatedUserLogListSchema(BaseModel):
    total_count: int
    page: int
    page_size: int = Field(default=10, ge=1, le=100)
    total_pages: int
    data: List[UserLogPublic]


class UserLogSearchRequestSchema(BaseModel):
    page: int = Field(default=1)
    page_size: int = Field(default=10, ge=1, le=100)
    filters: UserActivityLogFilterSchema


class SuperUserUpdateMe(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)
    ssh_username: str | None = Field(default=None, max_length=33)


class HostIpData(BaseModel):
    name: ValidatedDomainName
    ips: List[IPv4Address]


T = TypeVar("T")


class SshResponse(TypedDict):
    host: str
    stdout: str | None
    stderr: str | None
    returncode: int | None


class ExecutionStatus(str, Enum):
    OK = "OK"
    CREATED = "CREATED"
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    UNPROCESSABLE_ENTITY = "UNPROCESSABLE_ENTITY"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    @classmethod
    def from_code(cls, code: int) -> "ExecutionStatus":
        code_map = {
            200: cls.OK,
            201: cls.CREATED,
            400: cls.BAD_REQUEST,
            401: cls.UNAUTHORIZED,
            422: cls.UNPROCESSABLE_ENTITY,
            404: cls.NOT_FOUND,
            500: cls.INTERNAL_ERROR,
        }
        return code_map.get(code, cls.INTERNAL_ERROR)

    @classmethod
    def from_string(cls, status_str: str) -> "ExecutionStatus":
        normalized = status_str.strip().upper()

        for status in cls:
            if status.value.upper() == normalized:
                return status

        try:
            return cls(normalized)
        except ValueError:
            pass

        mappings = {
            "OK": cls.OK,
            "CREATED": cls.CREATED,
            "BAD REQUEST": cls.BAD_REQUEST,
            "UNAUTHORIZED": cls.UNAUTHORIZED,
            "UNPROCESSABLE ENTITY": cls.UNPROCESSABLE_ENTITY,
            "NOT FOUND": cls.NOT_FOUND,
            "INTERNAL ERROR": cls.INTERNAL_ERROR,
        }

        for key, value in mappings.items():
            if key.upper() == normalized:
                return value

        return cls.INTERNAL_ERROR

    @property
    def code(self) -> int:
        code_map = {
            self.OK: 200,
            self.CREATED: 201,
            self.BAD_REQUEST: 400,
            self.UNAUTHORIZED: 401,
            self.UNPROCESSABLE_ENTITY: 422,
            self.NOT_FOUND: 404,
            self.INTERNAL_ERROR: 500,
        }
        return code_map.get(self, 500)


class SignedExecutorResponse(GenericModel, Generic[T]):
    host: str
    status: ExecutionStatus
    code: int
    message: str
    payload: Optional[T] = None

    @model_validator(mode="before")
    @classmethod
    def convert_status(cls, data):
        if isinstance(data, dict):
            if isinstance(data.get("status"), str):
                data["status"] = ExecutionStatus.from_string(data["status"])
        return data

    @classmethod
    def from_ssh_response(
        cls: Type["SignedExecutorResponse[T]"], response: SshResponse
    ) -> "SignedExecutorResponse[T] | None":
        stdout = response.get("stdout")
        if not stdout:
            raise ValueError("No output found in SSH response.")

        try:
            parsed_response = json.loads(stdout)
            parsed_response["host"] = response.get("host")
            return cls.model_validate(parsed_response)
        except json.JSONDecodeError:
            raise ValueError("Failed to parse JSON from SSH response.")
        except Exception as e:
            raise ValueError(f"Error while parsing SSH response: {e}")
