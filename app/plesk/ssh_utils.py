import shlex
from fastapi import HTTPException


from app.AsyncSSHandler import execute_ssh_command, execute_ssh_commands_in_batch
from app.plesk.models import SubscriptionName, LinuxUsername, PleskServerDomain
from app.host_lists import PLESK_SERVER_LIST

PLESK_LOGLINK_CMD = "plesk login"
REDIRECTION_HEADER = r"&success_redirect_url=%2Fadmin%2Fsubscription%2Foverview%2Fid%2F"


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


async def build_restart_dns_service_command(domain: SubscriptionName) -> str:
    escaped_domain = shlex.quote(f'"{domain.lower()}"')
    return (
        f"plesk bin dns --off {escaped_domain} && plesk bin dns --on {escaped_domain}"
    )


async def is_domain_exist_on_server(
    host: PleskServerDomain, domain: SubscriptionName
) -> bool:
    get_subscription_name_cmd = (
        f'plesk db -Ne "SELECT name FROM domains WHERE webspace_id=0 AND id={domain}"'
    )
    result = await execute_ssh_command(host, get_subscription_name_cmd)
    subscription_name = result["stdout"]
    return not subscription_name == ""


async def restart_dns_service_for_domain(
    host: PleskServerDomain, domain: SubscriptionName
) -> None:
    if host in PLESK_SERVER_LIST:
        restart_dns_cmd = await build_restart_dns_service_command(domain)
        result = await execute_ssh_command(
            host=host, command=restart_dns_cmd, verbose=True
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

    else:
        raise ValueError(f"{host} is not valid Plesk server")


PLESK_DB_RUN_CMD = "plesk db -Ne"


def build_subscription_info_query(domain_to_find: str) -> str:
    return (
        "SELECT CASE WHEN webspace_id = 0 THEN id ELSE webspace_id END AS result "
        "FROM domains WHERE name LIKE '{0}'; "
        "SELECT name FROM domains WHERE id=(SELECT CASE WHEN webspace_id = 0 THEN id ELSE webspace_id END AS result FROM domains WHERE name LIKE '{0}'); "
        "SELECT pname, login FROM clients WHERE id=(SELECT cl_id FROM domains WHERE name LIKE '{0}'); "
        "SELECT name FROM domains WHERE webspace_id=(SELECT CASE WHEN webspace_id = 0 THEN id ELSE webspace_id END AS result FROM domains WHERE name LIKE '{0}');"
    ).format(domain_to_find)


def extract_subscription_details(answer) -> dict:
    stdout_lines = answer["stdout"].strip().split("\n")
    if len(stdout_lines) == 1:
        return None
    parsed_answer = {
        "host": answer["host"],
        "id": stdout_lines[0],
        "name": stdout_lines[1],
        "username": stdout_lines[2].split("\t")[0],
        "userlogin": stdout_lines[2].split("\t")[1],
        "domains": [stdout_lines[1]] + stdout_lines[3:],
    }
    return parsed_answer


async def build_plesk_db_command(query: str) -> str:
    return f'{PLESK_DB_RUN_CMD} \\"{query}\\"'


async def batch_ssh_execute(cmd: str):
    return await execute_ssh_commands_in_batch(
        server_list=PLESK_SERVER_LIST,
        command=cmd,
        verbose=True,
    )


async def fetch_subscription_info(domain_name: SubscriptionName, partial_search=False):
    lowercate_domain_name = domain_name.lower()
    query = (
        build_subscription_info_query(lowercate_domain_name)
        if not partial_search
        else build_subscription_info_query(lowercate_domain_name + "%")
    )
    ssh_command = await build_plesk_db_command(query)
    answers = await batch_ssh_execute(ssh_command)
    results = [
        extract_subscription_details(answer) for answer in answers if answer["stdout"]
    ]
    if not results:
        return None
    return results


async def _build_plesk_login_command(ssh_username: LinuxUsername) -> str:
    return f"{PLESK_LOGLINK_CMD} {ssh_username}"


async def _is_subscription_id_exist(
    host: PleskServerDomain, subscriptionId: str
) -> bool:
    get_subscription_name_cmd = f'plesk db -Ne "SELECT name FROM domains WHERE webspace_id=0 AND id={subscriptionId}"'
    result = await execute_ssh_command(host, get_subscription_name_cmd)
    subscription_name = result["stdout"]
    return not subscription_name == ""


async def fetch_plesk_login_link(
    host: PleskServerDomain, ssh_username: LinuxUsername
) -> str:
    cmd_to_run = await _build_plesk_login_command(ssh_username)
    result = await execute_ssh_command(host, cmd_to_run)
    login_link = result["stdout"]
    return login_link


async def generate_subscription_login_link(
    host: PleskServerDomain, subscription_id: int, ssh_username: LinuxUsername
) -> str:
    if not await _is_subscription_id_exist(host, subscription_id):
        raise HTTPException(
            status_code=404,
            detail=f"Subscription with {subscription_id} ID doesn't exist.",
        )

    plesk_login_link = await fetch_plesk_login_link(host, ssh_username)
    subscription_login_link = f"{plesk_login_link}{REDIRECTION_HEADER}{subscription_id}"

    return subscription_login_link
