from pydantic import (
    BaseModel,
    RootModel,
    StringConstraints,
    field_validator,
)

from typing import List
from typing_extensions import Annotated
from app.schemas import (
    SubscriptionName,
    SUBSCRIPTION_NAME_PATTERN,
    DomainName,
    PleskServerDomain,
)
from fastapi import Depends, Query

from app.host_lists import PLESK_SERVER_LIST

OPTIONALLY_FULLY_QUALIFIED_DOMAIN_NAME_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}\.?$"
)


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
