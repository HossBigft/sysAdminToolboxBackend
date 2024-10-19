from .host_lists import DNS_SERVER_LIST
from .ssh_async_executor import batch_ssh_command_result, batch_ssh_command_prepare
import re

DOMAIN_REGEX_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$"
)


def is_valid_domain(domain_name: str) -> bool:
    return 3 <= len(domain_name) <= 63 and bool(
        re.match(DOMAIN_REGEX_PATTERN, domain_name)
    )



async def getDomainZoneMasterAsync(
    domain_name: str, verbosity_flag=True, debug_flag=False
):
    if not is_valid_domain(domain_name):
        raise ValueError("Input string should be a valid domain name.")

    getZoneMasterCmd = f"cat /var/opt/isc/scls/isc-bind/zones/_default.nzf| grep '\\\"{''.join(domain_name)}\\\"' | grep -Po '((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\\b){{4}}' | head -n1"
    dnsAnswers = []
    dnsAnswers = await batch_ssh_command_prepare(
        server_list=DNS_SERVER_LIST,
        command=getZoneMasterCmd,
        verbose=debug_flag,
    )
    if verbosity_flag:
        return {"domain": f"{domain_name}", "answers": dnsAnswers}

    unique_zone_masters = list(set(answer["stdout"] for answer in dnsAnswers))
    return  {
        "domain": domain_name,
        "zone_master": unique_zone_masters,
    }
