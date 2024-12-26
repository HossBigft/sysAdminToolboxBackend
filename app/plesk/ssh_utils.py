import shlex
import re

from app.host_lists import PLESK_SERVER_LIST
from app.AsyncSSHandler import execute_ssh_command, execute_ssh_commands_in_batch
from app.plesk.models import DomainName, SubscriptionName
from app.models import SUBSCRIPTION_NAME_PATTERN


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


async def is_domain_exist_on_server(host: DomainName, domain: SubscriptionName) -> bool:
    get_subscription_name_cmd = (
        f'plesk db -Ne "SELECT name FROM domains WHERE webspace_id=0 AND id={domain}"'
    )
    result = await execute_ssh_command(host, get_subscription_name_cmd)
    subscription_name = result["stdout"]
    return not subscription_name == ""


async def restart_dns_service_for_domain(
    host: DomainName, domain: SubscriptionName
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


def is_valid_subscription_name(domain_name: str) -> bool:
    return 3 <= len(domain_name) <= 63 and bool(
        re.match(SUBSCRIPTION_NAME_PATTERN, domain_name)
    )


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


async def fetch_subscription_info(domain_name: str, partial_search=False):
    if not is_valid_subscription_name(domain_name):
        raise ValueError("Input string should be a valid domain name.")

    lowercate_domain_name = domain_name.lower()
    query = (
        build_subscription_info_query(lowercate_domain_name)
        if not partial_search
        else build_subscription_info_query(lowercate_domain_name + "%")
    )
    ssh_command = await build_plesk_db_command(query)
    answers = await batch_ssh_execute(ssh_command)
    results = [extract_subscription_details(answer) for answer in answers if answer["stdout"]]
    if not results:
        return None
    return results
