from pydantic import (
    BaseModel,
    RootModel,
    StringConstraints,
    model_serializer,
    field_validator,
)

from typing import List
from typing_extensions import Annotated
from pydantic.networks import IPvAnyAddress
from app.schemas import SubscriptionName, SUBSCRIPTION_NAME_PATTERN

from app.host_lists import PLESK_SERVER_LIST

OPTIONALLY_FULLY_QUALIFIED_DOMAIN_NAME_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}\.?$"
)

LINUX_USERNAME_PATTERN = r"^[a-z_]([a-z0-9_-]{0,31}|[a-z0-9_-]{0,30}\$)$"


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


class SubscriptionLoginLinkInput(BaseModel):
    host: Annotated[
        str,
        StringConstraints(
            min_length=3,
            max_length=253,
            pattern=OPTIONALLY_FULLY_QUALIFIED_DOMAIN_NAME_PATTERN,
        ),
    ]
    subscription_id: int
    model_config = {
        "json_schema_extra": {
example.com
        }
    }

    @field_validator("host")
    def validate_host(cls, v):
        if v not in PLESK_SERVER_LIST:
            raise ValueError(f"Host '{v}' is not Plesk server.")
        return v


class SubscriptionDetailsModel(BaseModel):
    host: DomainName
    id: str
    name: str
    username: str
    userlogin: str
    domains: List[SubscriptionName]


class SubscriptionListResponseModel(RootModel):
    root: List[SubscriptionDetailsModel]


class SetZonemasterInput(BaseModel):
    target_plesk_server: Annotated[
        str,
        StringConstraints(
            min_length=3,
            max_length=253,
            pattern=OPTIONALLY_FULLY_QUALIFIED_DOMAIN_NAME_PATTERN,
        ),
    ]
    domain: Annotated[
        str,
        StringConstraints(
            min_length=3,
            max_length=253,
            pattern=SUBSCRIPTION_NAME_PATTERN,
        ),
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
example.com
            ]
        }
    }

    @field_validator("target_plesk_server")
    def validate_host(cls, v):
        if v not in PLESK_SERVER_LIST:
            raise ValueError(f"Host '{v}' is not Plesk server.")
        return v


class LinuxUsername(BaseModel):
    name: (
        Annotated[
            str,
            StringConstraints(
                min_length=3,
                max_length=32,
                pattern=LINUX_USERNAME_PATTERN,
            ),
        ]
        | None
    )



