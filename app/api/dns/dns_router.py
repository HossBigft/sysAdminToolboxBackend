from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Request
from typing import Annotated

from app.api.dns.ssh_utils import (
    dns_get_domain_zone_master,
    dns_remove_domain_zone_master,
    dns_query_domain_zone_master,
)
from app.api.dns.dns_utils import resolve_record, RecordNotFoundError
from app.db.crud import (
    log_dns_zone_master_removal,
    log_dns_zone_master_fetch,
)
from app.api.dependencies import CurrentUser, SessionDep, RoleChecker
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
)


router = APIRouter(tags=["dns"], prefix="/dns")


@router.get(
    "/internal/resolve/a/",
    dependencies=[
        Depends(RoleChecker([UserRoles.USER, UserRoles.SUPERUSER, UserRoles.ADMIN]))
    ],
)
async def get_a_record(domain: Annotated[DomainName, Query()]) -> DomainARecordResponse:
    try:
        a_records = resolve_record(domain.name, "A")
        records = [IPv4Address(ip=ip) for ip in a_records]
        return DomainARecordResponse(domain=domain, records=records)
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/resolve/ptr/",
    dependencies=[
        Depends(RoleChecker([UserRoles.USER, UserRoles.SUPERUSER, UserRoles.ADMIN]))
    ],
)
async def get_ptr_record(ip: Annotated[IPv4Address, Query()]):
    try:
        ptr_records = resolve_record(str(ip), "PTR")
        records = [DomainName(name=domain) for domain in ptr_records]
        return PtrRecordResponse(ip=ip, records=records)
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


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
        zone_masters_dict = await dns_query_domain_zone_master(domain)
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
    try:
        mx_records = resolve_record(domain_str, "MX")
        records = [DomainName(name=domain) for domain in mx_records]
        return DomainMxRecordResponse(
            domain=DomainName(name=domain_str), records=records
        )
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


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
    try:
        ns_records = resolve_record(domain_str, "NS")
        records = [DomainName(name=domain) for domain in ns_records]
        return DomainNsRecordResponse(
            domain=DomainName(name=domain_str), records=records
        )
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


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
        curr_zonemaster = await dns_get_domain_zone_master(domain)
        await dns_remove_domain_zone_master(domain)
        request_ip = IPv4Address(ip=request.client.host)
        background_tasks.add_task(
            log_dns_zone_master_removal,
            session=session,
            user=current_user,
            current_zone_master=curr_zonemaster,
            domain=domain,
            ip=request_ip,
        )
        return Message(message="Zone master deleted successfully")
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
