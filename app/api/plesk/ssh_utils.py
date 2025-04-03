import shlex
import secrets
import string

from fastapi import HTTPException
from typing import TypedDict, List
from enum import IntEnum


from app.AsyncSSHandler import execute_ssh_command, execute_ssh_commands_in_batch
from app.host_lists import PLESK_SERVER_LIST
from app.schemas import PleskServerDomain, LinuxUsername
from app.api.plesk.plesk_schemas import SubscriptionName, TestMailData
from app.api.plesk.ssh_token_signer import SshToKenSigner

PLESK_LOGLINK_CMD = "plesk login"
REDIRECTION_HEADER = r"&success_redirect_url=%2Fadmin%2Fsubscription%2Foverview%2Fid%2F"
PLESK_DB_RUN_CMD_TEMPLATE = 'plesk db -Ne \\"{}\\"'
TEST_MAIL_LOGIN = "testhoster"
TEST_MAIL_PASSWORD_LENGTH = 14

Signer = SshToKenSigner()


class DomainStatus(IntEnum):
    ONLINE = 0
    SUBSCRIPTION_DISABLED = 2
    DISABLED_BY_ADMIN = 16
    DISABLED_BY_CLIENT = 64


class DomainState(TypedDict):
    domain: str
    status: str


class SubscriptionDetails(TypedDict):
    host: str
    id: str
    name: str
    username: str
    userlogin: str
    domains: List[str]
    domain_states: List[DomainState]
    is_space_overused: bool
    subscription_size_mb: int
    subscription_status: str


class DomainQueryResult(TypedDict):
    host: str
    id: str
    name: str
    username: str
    userlogin: str
    domains: List[str]
    domain_states: List[DomainState]
    is_space_overused: bool
    subscription_size_mb: int
    subscription_status: str


STATUS_MAPPING = {
    DomainStatus.ONLINE: "online",
    DomainStatus.SUBSCRIPTION_DISABLED: "subscription_is_disabled",
    DomainStatus.DISABLED_BY_ADMIN: "domain_disabled_by_admin",
    DomainStatus.DISABLED_BY_CLIENT: "domain_disabled_by_client",
}


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
    """
    Builds a SQL query string to search for domain information.
    Compatible with MySQL 5.7.
    """
    return f"""
    SELECT 
        base.subscription_id AS result,
        (SELECT name FROM domains WHERE id = base.subscription_id) AS name,
        (SELECT pname FROM clients WHERE id = base.cl_id) AS username,
        (SELECT login FROM clients WHERE id = base.cl_id) AS userlogin,
        (SELECT GROUP_CONCAT(CONCAT(d2.name, ':', d2.status) SEPARATOR ',')
        FROM domains d2 
        WHERE base.subscription_id IN (d2.id, d2.webspace_id)) AS domains,
        (SELECT overuse FROM domains WHERE id = base.subscription_id) as is_space_overused,
        (SELECT ROUND(real_size/1024/1024) FROM domains WHERE id = base.subscription_id) as subscription_size_mb,
        (SELECT status FROM domains WHERE id = base.subscription_id) as subscription_status
    FROM (
        SELECT 
            CASE 
                WHEN webspace_id = 0 THEN id 
                ELSE webspace_id 
            END AS subscription_id,
            cl_id,
            name
        FROM domains 
        WHERE name LIKE '{domain_to_find}'
    ) AS base;
    """


def get_domain_status_string(status_code: int) -> str:
    """Convert numeric status code to string representation."""
    try:
        domain_status = DomainStatus(status_code)
        return STATUS_MAPPING.get(domain_status, "unknown_status")
    except ValueError:
        return "unknown_status"


def parse_domain_states(domain_states_str: str) -> List[DomainState]:
    """Parse domain states string into list of dictionaries."""
    if not domain_states_str:
        return []

    domain_states = []
    for domain_status in domain_states_str.split(","):
        try:
            domain, status = domain_status.split(":")
            status_code = int(status)
            domain_states.append(
                {"domain": domain, "status": get_domain_status_string(status_code)}
            )
        except (ValueError, IndexError):
            continue
    return domain_states


def extract_subscription_details(answer) -> SubscriptionDetails | None:
    result_lines = answer["stdout"].strip().split("\n")[0].split("\t")

    domain_states = parse_domain_states(result_lines[4])
    subscription_details = SubscriptionDetails(
        host=answer["host"],
        id=result_lines[0],
        name=result_lines[1],
        username=result_lines[2],
        userlogin=result_lines[3],
        domains=[state["domain"] for state in domain_states],
        domain_states=domain_states,
        is_space_overused=result_lines[5].lower() == "true",
        subscription_size_mb=int(result_lines[6]),
        subscription_status=(
            get_domain_status_string(DomainStatus.SUBSCRIPTION_DISABLED)
            if int(result_lines[7]) == DomainStatus.SUBSCRIPTION_DISABLED
            else get_domain_status_string(DomainStatus.ONLINE)
        ),
    )

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
    return f"/usr/local/psa/admin/bin/mail_auth_view | grep -F '{TEST_MAIL_LOGIN}@{domain.name}' | tr -d '[:space:]' | cut -d '|' -f4-"


async def _build_create_testmail_command(
    domain: SubscriptionName, password: str
) -> str:
example.com


async def _generate_password(password_length: int) -> str:
    shell_quotation = {"'", '"', "`"}
    characters = "".join(
        c
        for c in (string.ascii_letters + string.digits + string.punctuation)
        if c not in shell_quotation
    )
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
) -> TestMailData:
    generated_login_link = f"https://webmail.{mail_domain.name}/roundcube/index.php?_user={TEST_MAIL_LOGIN}%40{mail_domain.name}"
    new_email_created = False
    password = await _get_testmail_password(host=host, mail_domain=mail_domain)
    if not password:
        password = await _generate_password(TEST_MAIL_PASSWORD_LENGTH)
        await _create_testmail(host=host, mail_domain=mail_domain, password=password)
        new_email_created = True
    return TestMailData(
        login_link=generated_login_link,
        password=password,
        new_email_created=new_email_created,
    )


async def get_public_key():
    return Signer.get_public_key_pem()


async def sign(command: str):
    return Signer.create_signed_token(command)
