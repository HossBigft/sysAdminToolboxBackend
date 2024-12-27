import shlex

from app.host_lists import DNS_SERVER_LIST
from app.AsyncSSHandler import execute_ssh_commands_in_batch
from app.models import SubscriptionName

ZONEFILE_PATH = "/var/opt/isc/scls/isc-bind/zones/_default.nzf"
DOMAIN_REGEX_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$"
)


async def build_zone_master_command(domain_name: SubscriptionName) -> str:
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
        verbose=True,
    )


async def get_domain_zonemaster_data(domain_name: SubscriptionName):
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


async def build_remove_zone_master_command(domain_name: SubscriptionName) -> str:
    escaped_domain = shlex.quote(f'\\"{domain_name.lower()}\\"')
    return f"/opt/isc/isc-bind/root/usr/sbin/rndc delzone -clean {escaped_domain}"


async def remove_domain_zone_master(domain: SubscriptionName):
    rm_zone_master_md = await build_remove_zone_master_command(domain)
    dnsAnswers = await batch_ssh_execute(rm_zone_master_md)
    for item in dnsAnswers:
        print(item["stderr"])
        if item["stderr"] and "not found" not in item["stderr"]:
            raise RuntimeError(
                f"DNS zone removal failed for host: {item['host']} "
                f"with error: {item['stderr']}"
            )
