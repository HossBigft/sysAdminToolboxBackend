import shlex
import secrets
import string

from fastapi import HTTPException
from typing import TypedDict, List


from app.AsyncSSHandler import execute_ssh_command, execute_ssh_commands_in_batch
from app.host_lists import PLESK_SERVER_LIST
from app.schemas import PleskServerDomain, LinuxUsername
from app.api.plesk.plesk_schemas import SubscriptionName, TestMailLoginData

PLESK_LOGLINK_CMD = "plesk login"
REDIRECTION_HEADER = r"&success_redirect_url=%2Fadmin%2Fsubscription%2Foverview%2Fid%2F"
PLESK_DB_RUN_CMD_TEMPLATE = 'plesk db -Ne \\"{}\\"'
TEST_MAIL_LOGIN = "testhoster"
TEST_MAIL_PASSWORD_LENGTH = 14


class SubscriptionDetails(TypedDict):
    host: str
    id: str
    name: str
    username: str
    userlogin: str
    domains: List[str]


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
) -> int | None:
    query_subscription_id_by_domain = f"SELECT CASE WHEN webspace_id = 0 THEN id ELSE webspace_id END AS result FROM domains WHERE name LIKE '{domain.name}'"

    fetch_subscription_id_by_domain_cmd = await build_plesk_db_command(
        query_subscription_id_by_domain
    )
    result = await execute_ssh_command(host.name, fetch_subscription_id_by_domain_cmd)

    if result["stdout"]:
        subscription_id = int(result["stdout"])
        return subscription_id
    else:
        return None


async def is_domain_exist_on_server(
    host: PleskServerDomain, domain: SubscriptionName
) -> bool:
    return await fetch_subscription_id_by_domain(host=host, domain=domain) is not None


async def restart_dns_service_for_domain(
    host: PleskServerDomain, domain: SubscriptionName
) -> None:
    restart_dns_cmd = await build_restart_dns_service_command(domain)
    result = await execute_ssh_command(
        host=host.name, command=restart_dns_cmd, verbose=True
    )
    match result["returncode"]:
        case 4:
            raise DomainNotFoundError(f"Domain {domain} does not exist on server")
        case 0:
            pass
        case _:
            raise CommandExecutionError(
                stderr=result["stderr"], return_code=result["returncode"]
            )


def build_subscription_info_query(domain_to_find: str) -> str:
    return (
        "SELECT CASE WHEN webspace_id = 0 THEN id ELSE webspace_id END AS result "
        "FROM domains WHERE name LIKE '{0}'; "
        "SELECT name FROM domains WHERE id=(SELECT CASE WHEN webspace_id = 0 THEN id ELSE webspace_id END AS result FROM domains WHERE name LIKE '{0}'); "
        "SELECT pname, login FROM clients WHERE id=(SELECT cl_id FROM domains WHERE name LIKE '{0}'); "
        "SELECT name FROM domains WHERE webspace_id=(SELECT CASE WHEN webspace_id = 0 THEN id ELSE webspace_id END AS result FROM domains WHERE name LIKE '{0}');"
    ).format(domain_to_find)


def extract_subscription_details(answer) -> SubscriptionDetails | None:
    stdout_lines = answer["stdout"].strip().split("\n")
    if len(stdout_lines) == 1:
        return None
    subscription_details: SubscriptionDetails = {
        "host": answer["host"],
        "id": stdout_lines[0],
        "name": stdout_lines[1],
        "username": stdout_lines[2].split("\t")[0],
        "userlogin": stdout_lines[2].split("\t")[1],
        "domains": [stdout_lines[1]] + stdout_lines[3:],
    }
    return subscription_details


async def batch_ssh_execute(cmd: str):
    return await execute_ssh_commands_in_batch(
        server_list=PLESK_SERVER_LIST,
        command=cmd,
        verbose=True,
    )


async def plesk_fetch_subscription_info(
    domain: SubscriptionName, partial_search=False
) -> List[SubscriptionDetails] | None:
    lowercate_domain_name = domain.name.lower()
    query = build_subscription_info_query(
        lowercate_domain_name if not partial_search else lowercate_domain_name + "%"
    )

    ssh_command = await build_plesk_db_command(query)

    answers = await batch_ssh_execute(ssh_command)

    results = [
        details
        for answer in answers
        if answer.get("stdout") and (details := extract_subscription_details(answer))
    ]

    return results if results else None


async def _build_plesk_login_command(ssh_username: LinuxUsername) -> str:
    return f"{PLESK_LOGLINK_CMD} {ssh_username}"


async def _is_subscription_id_exist(
    host: PleskServerDomain, subscriptionId: int
) -> bool:
    get_subscription_name_cmd = f'plesk db -Ne "SELECT name FROM domains WHERE webspace_id=0 AND id={subscriptionId}"'
    result = await execute_ssh_command(host.name, get_subscription_name_cmd)
    subscription_name = result["stdout"]
    return not subscription_name == ""


async def plesk_fetch_plesk_login_link(
    host: PleskServerDomain, ssh_username: LinuxUsername
) -> str | None:
    cmd_to_run = await _build_plesk_login_command(ssh_username)
    result = await execute_ssh_command(host.name, cmd_to_run)
    login_link = result["stdout"]
    return login_link


async def plesk_generate_subscription_login_link(
    host: PleskServerDomain, subscription_id: int, ssh_username: LinuxUsername
) -> str:
    if not await _is_subscription_id_exist(host, subscription_id):
        raise HTTPException(
            status_code=404,
            detail=f"Subscription with {subscription_id} ID doesn't exist.",
        )

    plesk_login_link = await plesk_fetch_plesk_login_link(host, ssh_username)
    subscription_login_link = f"{plesk_login_link}{REDIRECTION_HEADER}{subscription_id}"

    return subscription_login_link


async def _build_fetch_testmail_password_command(domain: SubscriptionName) -> str:
    return f"/usr/local/psa/admin/bin/mail_auth_view | grep -F '{TEST_MAIL_LOGIN}@{domain.name}' | tr -d '[:space:]' | awk -F'|' '{{print \\$4}}'"


async def _build_create_testmail_command(
    domain: SubscriptionName, password: str
) -> str:
example.com


async def _generate_password(password_length: int) -> str:
    characters = (
        string.ascii_letters + string.digits + string.punctuation
    )  # Includes specials
    password = "".join(secrets.choice(characters) for _ in range(password_length))
    return password


async def _get_testmail_password(
    host: PleskServerDomain, mail_domain: SubscriptionName
) -> str | None:
    command = await _build_fetch_testmail_password_command(mail_domain)
    result = await execute_ssh_command(host=host.name, command=command)
    password = result["stdout"]
    return password if password else None


async def _create_testmail(
    host: PleskServerDomain, mail_domain: SubscriptionName, password: str
) -> None:
    command = await _build_create_testmail_command(mail_domain, password)
    result = await execute_ssh_command(host=host.name, command=command)
    if result["returncode"] != 0:
        raise RuntimeError(
            f"Test mail creation failed on Plesk server: {result['host']} "
            f"with error: {result['stderr']}"
        )


async def plesk_get_testmail_login_data(
    host: PleskServerDomain, mail_domain: SubscriptionName
) -> TestMailLoginData:
    generated_login_link = f"https://webmail.{mail_domain.name}/roundcube/index.php?_user={TEST_MAIL_LOGIN}%40{mail_domain.name}"

    password = await _get_testmail_password(host=host, mail_domain=mail_domain)
    if not password:
        password = await _generate_password(TEST_MAIL_PASSWORD_LENGTH)
        await _create_testmail(host=host, mail_domain=mail_domain, password=password)
    return TestMailLoginData(login_link=generated_login_link, password=password)
