from .host_lists import PLESK_SERVER_LIST
from .ssh_async_executor import batch_ssh_command_prepare
import re

DOMAIN_REGEX_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$"
)
PLESK_DB_RUN_CMD = "plesk db -Ne"


def is_valid_domain(domain_name: str) -> bool:
    return 3 <= len(domain_name) <= 63 and bool(
        re.match(DOMAIN_REGEX_PATTERN, domain_name)
    )


def build_query(domain_to_find: str) -> str:
    return (
        "SELECT CASE WHEN webspace_id = 0 THEN id ELSE webspace_id END AS result "
        "FROM domains WHERE name LIKE '{0}'; "
        "SELECT name FROM domains WHERE id=(SELECT CASE WHEN webspace_id = 0 THEN id ELSE webspace_id END AS result FROM domains WHERE name LIKE '{0}'); "
        "SELECT pname, login FROM clients WHERE id=(SELECT cl_id FROM domains WHERE name LIKE '{0}'); "
        "SELECT name FROM domains WHERE webspace_id=(SELECT CASE WHEN webspace_id = 0 THEN id ELSE webspace_id END AS result FROM domains WHERE name LIKE '{0}');"
    ).format(domain_to_find)


def parse_answer(answer) -> dict:
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


async def build_ssh_command(query: str) -> str:
    return f'{PLESK_DB_RUN_CMD} \\"{query}\\"'


async def batch_ssh_execute(cmd: str):
    return await batch_ssh_command_prepare(
        server_list=PLESK_SERVER_LIST,
        command=cmd,
        verbose=True,
    )


async def query_subscription_info_by_domain(domain_name: str, partial_search=False):
    if not is_valid_domain(domain_name):
        raise ValueError("Input string should be a valid domain name.")

    lowercate_domain_name = domain_name.lower()
    query = (
        build_query(lowercate_domain_name)
        if not partial_search
        else build_query(lowercate_domain_name + "%")
    )
    ssh_command = await build_ssh_command(query)
    answers = await batch_ssh_execute(ssh_command)
    results = [parse_answer(answer) for answer in answers if answer["stdout"]]
    if not results:
        return None
    return results
