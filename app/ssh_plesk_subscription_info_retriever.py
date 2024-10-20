from .host_lists import PLESK_SERVER_LIST
from .ssh_async_executor import batch_ssh_command_prepare
import re

DOMAIN_REGEX_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$"
)


def is_valid_domain(domain_name: str) -> bool:
    return 3 <= len(domain_name) <= 63 and bool(
        re.match(DOMAIN_REGEX_PATTERN, domain_name)
    )


def build_query(domain_to_find: str) -> str:
    return (
        "SELECT CASE WHEN webspace_id = 0 THEN id ELSE webspace_id END AS result "
        "FROM domains WHERE name LIKE %s; "
        "SELECT name FROM domains WHERE id=(SELECT CASE WHEN webspace_id = 0 THEN id ELSE webspace_id END AS result FROM domains WHERE name LIKE %s); "
        "SELECT pname, login FROM clients WHERE id=(SELECT cl_id FROM domains WHERE name LIKE %s); "
        "SELECT name FROM domains WHERE webspace_id=(SELECT CASE WHEN webspace_id = 0 THEN id ELSE webspace_id END AS result FROM domains WHERE name LIKE %s);"
    ), (domain_to_find, domain_to_find, domain_to_find, domain_to_find)


def parse_answer(answer) -> dict:
    stdout_lines = answer["stdout"].strip().split("\n")
    return {
        "host": answer["host"],
        "id": stdout_lines[0],
        "name": stdout_lines[1],
        "username": stdout_lines[2].split("\t")[0],
        "userlogin": stdout_lines[2].split("\t")[1],
        "domains": stdout_lines[3:],
    }


async def query_domain_info(domain_name: str, verbose_flag=True, partial_search=False):
    if not is_valid_domain(domain_name):
        raise ValueError("Input string should be a valid domain name.")

    query = (
        build_query(domain_name)
        if not partial_search
        else build_query(domain_name + "%")
    )

    answers = await batch_ssh_command_prepare(
        PLESK_SERVER_LIST,
        f'plesk db -Ne \\"{query}\\"',
        verbose=verbose_flag,
    )

    results = [parse_answer(answer) for answer in answers if answer["stdout"]]
    return results
