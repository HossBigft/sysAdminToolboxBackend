from fastapi import HTTPException

from app.core.AsyncSSHandler import execute_ssh_commands_in_batch
from app.schemas import (
    SubscriptionName,
    PleskServerDomain,
    DomainName,
    DNS_SERVER_LIST,
    SignedExecutorResponse,
    ExecutionStatus,
)
from app.api.dns.dns_utils import resolve_record
from app.api.dependencies import get_token_signer

_token_signer = get_token_signer()


async def batch_ssh_execute(cmd: str):
    return await execute_ssh_commands_in_batch(
        server_list=DNS_SERVER_LIST,
        command=cmd,
        verbose=True,
    )


async def dns_query_domain_zone_master(domain: SubscriptionName | DomainName):
    responses = await batch_ssh_execute(
        "execute "
        + _token_signer.create_signed_token(f"NS.GET_ZONE_MASTER {domain.name}")
    )

    results = []
    for raw, parsed in zip(
        responses, map(SignedExecutorResponse.from_ssh_response, responses)
    ):
        if parsed.payload:
            results.append(
                {
                    "ns": raw["host"],
                    "zone_master": parsed.payload["zonemaster_ip"],
                }
            )

    if not results:
        return None

    return {"domain": domain.name, "answers": results}


async def dns_remove_domain_zone_master(domain: SubscriptionName | DomainName):
    responses = await batch_ssh_execute(
        "execute " + _token_signer.create_signed_token(f"NS.REMOVE_ZONE {domain.name}")
    )

    for parsedAnswer in map(SignedExecutorResponse.from_ssh_response, responses):
        if parsedAnswer.status is not (ExecutionStatus.OK or ExecutionStatus.NOT_FOUND):
            raise HTTPException(status_code=500)


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
