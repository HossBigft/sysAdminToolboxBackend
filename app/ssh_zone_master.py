from .host_lists import DNS_SERVER_LIST
from .ssh_async_executor import batch_ssh_command_prepare
import re
import shlex

ZONEFILE_PATH = "/var/opt/isc/scls/isc-bind/zones/_default.nzf"
DOMAIN_REGEX_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$"
)


def is_valid_domain(domain_name: str) -> bool:
    return 3 <= len(domain_name) <= 63 and bool(
        re.match(DOMAIN_REGEX_PATTERN, domain_name)
    )


def build_zone_master_command(domain_name: str) -> str:
    escaped_domain = shlex.quote(f'\\"{domain_name.lower()}\\"')
    return (
        f"cat {ZONEFILE_PATH} | "
        f"grep {escaped_domain} | "
        r"grep -Po '((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}' | "
        "head -n1"
    )


async def batch_ssh_execute(cmd: str):
    return await batch_ssh_command_prepare(
        server_list=DNS_SERVER_LIST,
        command=cmd,
        verbose=False,
    )


async def getDomainZoneMaster(domain_name: str):
    if not is_valid_domain(domain_name):
        raise ValueError("Input string should be a valid domain name.")
    getZoneMasterCmd = build_zone_master_command(domain_name)
    dnsAnswers = await batch_ssh_execute(getZoneMasterCmd)
    dnsAnswers = [
        {"ns": answer["host"], "zone_master": answer["stdout"]}
        for answer in dnsAnswers
        if answer["stdout"]
    ]
    if not dnsAnswers:
        return None
    return {"domain": f"{domain_name}", "answers": dnsAnswers}
