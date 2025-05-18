from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Request
from typing import Annotated

from app.dns.dns_utils import resolve_record, RecordNotFoundError
from app.db.crud import (
    log_dns_zone_master_fetch,
)
from app.core.dependencies import CurrentUser, SessionDep, RoleChecker
from app.schemas import (
    UserRoles,
    DomainName,
    DomainARecordResponse,
    PtrRecordResponse,
    IPv4Address,
    DomainMxRecordResponse,
    DomainNsRecordResponse,
    Message,
    SubscriptionName,
    HostIpData,
)
from app.core.DomainMapper import HOSTS
from app.dns.dns_service import DNSService
from app.core_utils.logger import log_dns_remove_zone
router = APIRouter(tags=["dns"], prefix="/dns")


@router.get(
    "/internal/resolve/a/",
    dependencies=[
        Depends(RoleChecker([UserRoles.USER, UserRoles.SUPERUSER, UserRoles.ADMIN]))
    ],
)
async def get_a_record(domain: Annotated[DomainName, Query()]) -> DomainARecordResponse:
    a_records = resolve_record(domain.name, "A")
    if not a_records:
        raise HTTPException(status_code=404, detail=f"A record for {domain} not found.")
    records = [IPv4Address(ip=ip) for ip in a_records]
    return DomainARecordResponse(domain=domain, records=records)


@router.get(
    "/resolve/ptr/",
    dependencies=[
        Depends(RoleChecker([UserRoles.USER, UserRoles.SUPERUSER, UserRoles.ADMIN]))
    ],
)
async def get_ptr_record(ip: Annotated[IPv4Address, Query()]):
    ptr_records = resolve_record(str(ip), "PTR")
    if not ptr_records:
        raise HTTPException(status_code=404, detail=f"PTR record for {ip} not found.")
    records = [DomainName(name=domain) for domain in ptr_records]
    return PtrRecordResponse(ip=ip, records=records)


@router.get(
    "/internal/zonemaster/",
    dependencies=[Depends(RoleChecker([UserRoles.SUPERUSER, UserRoles.ADMIN]))],
)
async def get_zone_master_from_dns_servers(
        session: SessionDep,
        background_tasks: BackgroundTasks,
        current_user: CurrentUser,
        domain: Annotated[SubscriptionName, Depends()],
        request: Request,
):
    try:
        zone_masters_dict = await DNSService().get_zone_masters(domain)
        if not zone_masters_dict:
            raise HTTPException(
                status_code=404,
                detail=f"Zone master for domain [{domain.name}] not found.",
            )

        request_ip = IPv4Address(ip=request.client.host)
        background_tasks.add_task(
            log_dns_zone_master_fetch,
            session=session,
            user=current_user,
            domain=domain,
            ip=request_ip,
        )
        return zone_masters_dict
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/internal/resolve/mx/",
    dependencies=[
        Depends(RoleChecker([UserRoles.USER, UserRoles.SUPERUSER, UserRoles.ADMIN]))
    ],
)
async def get_mx_record(
        domain: Annotated[DomainName, Query()],
) -> DomainMxRecordResponse:
    domain_str = domain.name
    mx_records = resolve_record(domain_str, "MX")
    if not mx_records:
        raise HTTPException(
            status_code=404, detail=f"MX record for {domain} not found."
        )
    records = [DomainName(name=domain) for domain in mx_records]
    return DomainMxRecordResponse(domain=DomainName(name=domain_str), records=records)


@router.get(
    "/resolve/ns/",
    dependencies=[
        Depends(RoleChecker([UserRoles.USER, UserRoles.SUPERUSER, UserRoles.ADMIN]))
    ],
)
async def get_ns_records(
        domain: Annotated[DomainName, Query()],
) -> DomainNsRecordResponse:
    domain_str = domain.name
    ns_records = resolve_record(domain_str, "NS")
    if not ns_records:
        raise HTTPException(
            status_code=404, detail=f"NS record for {domain} not found."
        )
    records = [DomainName(name=domain) for domain in ns_records]
    return DomainNsRecordResponse(domain=DomainName(name=domain_str), records=records)


@router.delete(
    "/internal/zonemaster/",
    dependencies=[Depends(RoleChecker([UserRoles.SUPERUSER, UserRoles.ADMIN]))],
)
async def delete_zone_file_for_domain(
        session: SessionDep,
        background_tasks: BackgroundTasks,
        current_user: CurrentUser,
        domain: Annotated[DomainName, Query()],
        request: Request,
):
    try:
        zone_masters = await DNSService().get_zone_masters(domain)
        curr_zonemaster = ", ".join([entry["ns"] for entry in zone_masters["answers"]])

        await DNSService().remove_zone(domain)

        background_tasks.add_task(
            log_dns_remove_zone,
            session=session,
            user=current_user,
            current_zonemaster=curr_zonemaster,
            domain=domain,
            request=request,
        )
        return Message(message="Zone master deleted successfully")
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/internal/hostbydomain",
    dependencies=[Depends(RoleChecker([UserRoles.SUPERUSER, UserRoles.ADMIN]))],
    response_model=HostIpData,
)
async def resolve_host_by_domain(
        domain: Annotated[DomainName, Depends()],
) -> HostIpData:
    resolved_host = HOSTS.resolve_domain(domain.name)

    if not resolved_host:
        raise HTTPException(
            status_code=404, detail=f"No host found with domain [{domain}]."
        )
    return resolved_host


@router.get(
    "/internal/hostbyip",
    dependencies=[Depends(RoleChecker([UserRoles.SUPERUSER, UserRoles.ADMIN]))],
    response_model=HostIpData,
)
async def resolve_host_by_ip(
        ip: Annotated[IPv4Address, Depends()],
) -> HostIpData:
    resolved_host = HOSTS.resolve_ip(ip)

    if not resolved_host:
        raise HTTPException(
            status_code=404, detail=f"No host found with domain [{ip.ip}]."
        )
    return resolved_host
