import shlex

from app.host_lists import DNS_SERVER_LIST
from app.AsyncSSHandler import execute_ssh_commands_in_batch
from app.schemas import SubscriptionName, PleskServerDomain, DomainName
from app.api.dns.dns_utils import resolve_record

ZONEFILE_PATH = "/var/opt/isc/scls/isc-bind/zones/_default.nzf"
DOMAIN_REGEX_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$"
)


async def build_get_zone_master_command(domain: SubscriptionName | DomainName) -> str:
    escaped_domain = shlex.quote(domain.name.lower())
    return (
        f"cat {ZONEFILE_PATH} | "
        f"grep -F {escaped_domain} | "
        r"grep -Po '((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}' | "
        "head -n1"
    )


async def batch_ssh_execute(cmd: str):
    return await execute_ssh_commands_in_batch(
        server_list=DNS_SERVER_LIST,
        command=cmd,
        verbose=True,
    )


async def dns_query_domain_zone_master(domain: SubscriptionName | DomainName):
    getZoneMasterCmd = await build_get_zone_master_command(domain)
    dnsAnswers = await batch_ssh_execute(getZoneMasterCmd)
    dnsAnswers = [
        {"ns": answer["host"], "zone_master": answer["stdout"]}
        for answer in dnsAnswers
        if answer["stdout"]
    ]
    if not dnsAnswers:
        return None
    return {"domain": f"{domain.name}", "answers": dnsAnswers}


async def build_remove_zone_master_command(
    domain: SubscriptionName | DomainName,
) -> str:
    escaped_domain = shlex.quote(domain.name.lower())
    return f"/opt/isc/isc-bind/root/usr/sbin/rndc delzone -clean {escaped_domain}"


async def dns_remove_domain_zone_master(domain: SubscriptionName | DomainName):
    rm_zone_master_md = await build_remove_zone_master_command(domain)
    dnsAnswers = await batch_ssh_execute(rm_zone_master_md)
    for item in dnsAnswers:
        if item["stderr"] and "not found" not in item["stderr"]:
            raise RuntimeError(
                f"DNS zone removal failed for host: {item['host']} "
                f"with error: {item['stderr']}"
            )


async def dns_get_domain_zone_master(
    domain: SubscriptionName | DomainName,
) -> set[PleskServerDomain] | None:
    zonemaster_data = await dns_query_domain_zone_master(domain=domain)
    if zonemaster_data is None:
        return None

    zonemaster_ip_set = {answer["zone_master"] for answer in zonemaster_data["answers"]}
    zonemaster_domains_set = set()
    for zonemaster in zonemaster_ip_set:
        zonemaster_domains_set.update(resolve_record(record=zonemaster, type="PTR"))

    return zonemaster_domains_set
