from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from typing import Annotated

from app.dns.ssh_utils import (
    dns_get_domain_zone_master,
    dns_remove_domain_zone_master,
    dns_query_domain_zone_master,
)
from app.dns.dns_utils import resolve_record, RecordNotFoundError
from app.crud import (
    add_dns_remove_zone_master_log_entry,
    add_dns_get_zone_master_log_entry,
)
from app.api.dependencies import CurrentUser, SessionDep, RoleChecker
from app.models import (
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
        a_records = resolve_record(domain.domain, "A")
        records = [IPv4Address(ip) for ip in a_records]
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
        records = [DomainName(domain=domain) for domain in ptr_records]
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
    domain: Annotated[SubscriptionName, Query()],
):
    try:
        zone_masters_dict = await dns_query_domain_zone_master(domain)
        if not zone_masters_dict:
            raise HTTPException(
                status_code=404,
                detail=f"Zone master for domain [{domain.domain}] not found.",
            )
        background_tasks.add_task(
            add_dns_get_zone_master_log_entry,
            session=session,
            db_user=current_user,
            domain=domain,
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
    domain_str = domain.domain
    try:
        mx_records = resolve_record(domain_str, "MX")
        records = [DomainName(domain=domain) for domain in mx_records]
        return DomainMxRecordResponse(
            domain=DomainName(domain=domain_str), records=records
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
    domain_str = domain.domain
    try:
        ns_records = resolve_record(domain_str, "NS")
        records = [DomainName(domain=domain) for domain in ns_records]
        return DomainNsRecordResponse(
            domain=DomainName(domain=domain_str), records=records
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
    domain: Annotated[SubscriptionName, Query()],
):
    try:
        curr_zonemaster = await dns_get_domain_zone_master(domain)
        await dns_remove_domain_zone_master(domain)
        background_tasks.add_task(
            add_dns_remove_zone_master_log_entry,
            session=session,
            db_user=current_user,
            current_zone_master=DomainName(domain=str(curr_zonemaster)),
        )
        return Message(message="Zone master deleted successfully")
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
