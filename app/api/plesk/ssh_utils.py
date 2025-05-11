import shlex
import secrets
import string
import random
import json

from fastapi import HTTPException
from typing import TypedDict, List
from enum import IntEnum

from app.AsyncSSHandler import execute_ssh_command, execute_ssh_commands_in_batch
from app.api.dependencies import get_token_signer

from app.schemas import PleskServerDomain, LinuxUsername, PLESK_SERVER_LIST
from app.api.plesk.plesk_schemas import (
    SubscriptionName,
    TestMailData,
    SubscriptionDetailsModel,
)
from app.DomainMapper import HOSTS

PLESK_LOGLINK_CMD = "plesk login"
REDIRECTION_HEADER = r"&success_redirect_url=%2Fadmin%2Fsubscription%2Foverview%2Fid%2F"
PLESK_DB_RUN_CMD_TEMPLATE = 'plesk db -Ne \\"{}\\"'
TEST_MAIL_LOGIN = "testhoster"
TEST_MAIL_PASSWORD_LENGTH = 14

_token_signer = get_token_signer()


class PleskServiceError(Exception):
    """Base exception for Plesk service operations"""

    pass


class DomainNotFoundError(PleskServiceError):
    """Raised when domain doesn't exist on server"""

    pass


class CommandExecutionError(PleskServiceError):
    """Raised when command execution fails"""

    def __init__(self, stderr: str, return_code: int | None):
        self.stderr = stderr
        self.return_code = return_code
        super().__init__(f"Command failed with return code {return_code}: {stderr}")


async def build_plesk_db_command(query: str) -> str:
    return PLESK_DB_RUN_CMD_TEMPLATE.format(query)


async def build_restart_dns_service_command(domain: SubscriptionName) -> str:
    escaped_domain = shlex.quote(f'"{domain.name.lower()}"')
    return (
        f"plesk bin dns --off {escaped_domain} && plesk bin dns --on {escaped_domain}"
    )


async def fetch_subscription_id_by_domain(
    host: PleskServerDomain, domain: SubscriptionName
) -> dict | None:
    result = await execute_ssh_command(
        host.name,
        command="execute "
        + _token_signer.create_signed_token(
            f"PLESK.GET_SUBSCRIPTION_ID_BY_DOMAIN {domain.name}"
        ),
    )

    if result["stdout"]:
        id_list = json.loads(result["stdout"])
        return id_list
    else:
        return None


async def is_domain_exist_on_server(
    host: PleskServerDomain, domain: SubscriptionName
) -> bool:
    return await fetch_subscription_id_by_domain(host=host, domain=domain) is not None


async def restart_dns_service_for_domain(
    host: PleskServerDomain, domain: SubscriptionName
) -> None:
    await execute_ssh_command(
        host=host.name,
        command="execute "
        + _token_signer.create_signed_token(f"PLESK.RESTART_DNS_SERVICE {domain.name}"),
        verbose=True,
    )


async def batch_ssh_execute(cmd: str):
    return await execute_ssh_commands_in_batch(
        server_list=PLESK_SERVER_LIST,
        command=cmd,
        verbose=True,
    )


async def plesk_fetch_subscription_info(
    domain: SubscriptionName,
) -> List[SubscriptionDetailsModel] | None:
    lowercase_domain_name = domain.name.lower()
    ssh_command = _token_signer.create_signed_token(
        f"PLESK.FETCH_SUBSCRIPTION_INFO {lowercase_domain_name}"
    )
    answers = await batch_ssh_execute("execute " + ssh_command)

    results = []
    for answer in answers:
        raw = answer.get("stdout")
        host_str = answer.get("host")
        if not raw or not host_str:
            continue

        try:
            parsed_list = json.loads(raw)  # This is expected to be a list of dicts
            for item in parsed_list:
                model_data = {
                    "host": HOSTS.resolve_domain(host_str),
                    "id": item["id"],
                    "name": item["name"],
                    "username": item["username"],
                    "userlogin": item["userlogin"],
                    "domain_states": item["domain_states"],
                    "domains": [
                        SubscriptionName(name=ds["domain"])
                        for ds in item["domain_states"]
                    ],
                    "is_space_overused": item["is_space_overused"],
                    "subscription_size_mb": item["subscription_size_mb"],
                    "subscription_status": item["subscription_status"],
                }
                model = SubscriptionDetailsModel.model_validate(model_data)
                results.append(model)

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            print(f"Failed to parse response from host {host_str}: {e}")

    return results if results else None


async def plesk_generate_subscription_login_link(
    host: PleskServerDomain, subscription_id: int, ssh_username: LinuxUsername
) -> str | None:
    result = await execute_ssh_command(
        host=host.name,
        command="execute "
        + _token_signer.create_signed_token(
            f"PLESK.GET_LOGIN_LINK {subscription_id} {ssh_username}"
        ),
    )
    subscription_login_link = result["stdout"]
    if not subscription_login_link:
        return None
    return subscription_login_link


async def plesk_get_testmail_login_data(
    host: PleskServerDomain, mail_domain: SubscriptionName
) -> TestMailData | None:
    result = await execute_ssh_command(
        host=host,
        command="execute "
        + _token_signer.create_signed_token(
            f"PLESK.GET_TESTMAIL_CREDENTIALS {mail_domain.name}"
        ),
    )

    if result["stdout"]:
        data_dict = json.loads(result["stdout"])
        return TestMailData.model_validate(data_dict)
    else:
        return None
