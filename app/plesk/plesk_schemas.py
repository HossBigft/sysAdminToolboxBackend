import re
import string

from pydantic import (
    BaseModel,
    RootModel,
    StringConstraints,
    field_validator,
    ConfigDict,
)

from typing import List, Dict
from typing_extensions import Annotated
from app.schemas import (
    SubscriptionName,
    SUBSCRIPTION_NAME_PATTERN,
    OPTIONALLY_FULLY_QUALIFIED_DOMAIN_NAME_PATTERN,
    PLESK_SERVER_LIST,
    HostIpData
)


WEBMAIL_LOGIN_LINK_PATTERN = r"^https:\/\/webmail\.(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,6}\/roundcube\/index\.php\?_user=[a-zA-Z0-9._%+-]+%40(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,6}$"


SPECIAL_CHARS = re.escape(string.punctuation)  # Escapes all special chars

EMAIL_PASSWORD_PATTERN = re.compile(
    rf"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d{SPECIAL_CHARS}]*$"
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
            "examples": [{"host": PLESK_SERVER_LIST[0], "subscription_id": 1124}]
        }
    }

    @field_validator("host")
    def validate_host(cls, v):
        if v not in PLESK_SERVER_LIST:
            raise ValueError(f"Host '{v}' is not Plesk server.")
        return v


class SubscriptionDetailsModel(BaseModel):
    host: HostIpData   
    id: str
    name: str
    username: str
    userlogin: str
    domains: List[SubscriptionName]
    domain_states: List[Dict[str, str]]
    is_space_overused: bool
    subscription_size_mb: int
    subscription_status: str


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
                {"target_plesk_server": PLESK_SERVER_LIST[0], "domain": "domain.kz"}
            ]
        }
    }

    @field_validator("target_plesk_server")
    def validate_host(cls, v):
        if v not in PLESK_SERVER_LIST:
            raise ValueError(f"Host '{v}' is not Plesk server.")
        return v


class TestMailCredentials(BaseModel):
    model_config = ConfigDict(regex_engine="python-re")
    login_link: Annotated[
        str,
        StringConstraints(
            pattern=WEBMAIL_LOGIN_LINK_PATTERN,
        ),
    ]
    password: Annotated[
        str,
        StringConstraints(min_length=5, max_length=255, pattern=EMAIL_PASSWORD_PATTERN),
    ]
    email: str


class TestMailData(TestMailCredentials):
    new_email_created: bool

class LoginLinkData(BaseModel):
    login_link:str
    subscription_name:str
