import shlex

from app.AsyncSSHandler import execute_ssh_commands_in_batch
from app.schemas import SubscriptionName, PleskServerDomain, DomainName, DNS_SERVER_LIST
from app.api.dns.dns_utils import resolve_record
from app.api.dependencies import get_token_signer

ZONEFILE_PATH = "/var/opt/isc/scls/isc-bind/zones/_default.nzf"
DOMAIN_REGEX_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$"
)


async def build_get_zone_master_command(domain: SubscriptionName | DomainName) -> str:
    escaped_domain = shlex.quote('\\"' + domain.name.lower())
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


_token_signer = get_token_signer()


async def dns_query_domain_zone_master(domain: SubscriptionName | DomainName):
    dnsAnswers = await batch_ssh_execute(
        "execute "
        + _token_signer.create_signed_token(f"NS.GET_ZONE_MASTER {domain.name}")
    )
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
    dnsAnswers = await batch_ssh_execute("execute " + _token_signer.create_signed_token(f"NS.REMOVE_ZONE {domain.name}"))
    for item in dnsAnswers:
        if item["stderr"] and "not found" not in item["stderr"]:
            raise RuntimeError(
                f"DNS zone removal failed for host: {item['host']} "
                f"with error: {item['stderr']}"
            )


async def dns_get_domain_zone_master(
    domain: SubscriptionName | DomainName,
) -> PleskServerDomain | str | None:
    zonemaster_data = await dns_query_domain_zone_master(domain=domain)
    if zonemaster_data is None:
        return None

    zonemaster_ip_set = {answer["zone_master"] for answer in zonemaster_data["answers"]}
    zonemaster_domains_set = set()
    for zonemaster in zonemaster_ip_set:
        zonemaster_domain = resolve_record(record=zonemaster, type="PTR")
        if zonemaster_domain:
            zonemaster_domains_set.update(zonemaster_domain)
    if not zonemaster_domains_set:
        return ",".join(str(ip) for ip in zonemaster_ip_set)
    return ",".join(str(ip) for ip in zonemaster_domains_set)
