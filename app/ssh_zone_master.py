from .host_lists import DNS_SERVER_LIST
from .ssh_async_executor import execute_ssh_commands_in_batch
import re
import shlex

ZONEFILE_PATH = "/var/opt/isc/scls/isc-bind/zones/_default.nzf"
DOMAIN_REGEX_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$"
)


async def is_valid_domain(domain_name: str) -> bool:
    return 3 <= len(domain_name) <= 63 and bool(
        re.match(DOMAIN_REGEX_PATTERN, domain_name)
    )


async def build_zone_master_command(domain_name: str) -> str:
    escaped_domain = shlex.quote(f'\\"{domain_name.lower()}\\"')
    return (
        f"cat {ZONEFILE_PATH} | "
        f"grep {escaped_domain} | "
        r"grep -Po '((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}' | "
        "head -n1"
    )


async def batch_ssh_execute(cmd: str):
    return await execute_ssh_commands_in_batch(
        server_list=DNS_SERVER_LIST,
        command=cmd,
        verbose=False,
    )


async def getDomainZoneMaster(domain_name: str):
    if not await is_valid_domain(domain_name):
        raise ValueError("Input string should be a valid domain name.")
    getZoneMasterCmd = await build_zone_master_command(domain_name)
    dnsAnswers = await batch_ssh_execute(getZoneMasterCmd)
    dnsAnswers = [
        {"ns": answer["host"], "zone_master": answer["stdout"]}
        for answer in dnsAnswers
        if answer["stdout"]
    ]
    if not dnsAnswers:
        return None
    return {"domain": f"{domain_name}", "answers": dnsAnswers}


async def build_remove_zone_master_command(domain_name: str) -> None:
    escaped_domain = shlex.quote(f'\\"{domain_name.lower()}\\"')
    return f"/opt/isc/isc-bind/root/usr/sbin/rndc delzone -clean {escaped_domain}"


async def remove_domain_zone_master(domain_name: str):
    if not await is_valid_domain(domain_name):
        raise ValueError("Input string should be a valid domain name.")
    rm_zone_master_md = await build_remove_zone_master_command(domain_name)
    dnsAnswers = await batch_ssh_execute(rm_zone_master_md)
    for item in dnsAnswers:
        if item["stderr"]:
            raise RuntimeError(
                f"DNS zone removal failed for host: {item['host']} "
                f"with error: {item['stderr']}"
            )
