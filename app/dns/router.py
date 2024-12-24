from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from pydantic.networks import IPvAnyAddress
from typing import Annotated

from app.dns.ssh_utils import getDomainZoneMaster, remove_domain_zone_master
from app.dns_resolver import resolve_record, RecordNotFoundError
from app.crud import add_action_to_history
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
)


router = APIRouter(tags=["dns"], prefix="/dns")


@router.get(
    "/internal/resolve/a/",
    dependencies=[
        Depends(RoleChecker([UserRoles.USER, UserRoles.SUPERUSER, UserRoles.ADMIN]))
    ],
)
async def get_a_record(domain: Annotated[DomainName, Query()]) -> DomainARecordResponse:
    domain_str = domain.domain
    try:
        a_records = resolve_record(domain_str, "A")
        records = [IPv4Address(ip=ip) for ip in a_records]
        return DomainARecordResponse(
            domain=DomainName(domain=domain_str), records=records
        )
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/resolve/ptr/",
    dependencies=[
        Depends(RoleChecker([UserRoles.USER, UserRoles.SUPERUSER, UserRoles.ADMIN]))
    ],
)
async def get_ptr_record(
    ip: IPvAnyAddress,
):
    try:
        ptr_records = resolve_record(str(ip), "PTR")
        records = [DomainName(domain=domain) for domain in ptr_records]
        return PtrRecordResponse(ip=IPv4Address(ip=ip), records=records)
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
    domain: Annotated[DomainName, Query()],
):
    domain_str = domain.domain
    try:
        zone_masters_dict = await getDomainZoneMaster(domain_str)
        if not zone_masters_dict:
            raise HTTPException(
                status_code=404,
                detail=f"Zone master for domain [{domain_str}] not found.",
            )
        background_tasks.add_task(
            add_action_to_history,
            session=session,
            db_user=current_user,
            action=f"get zonemaster of domain [{domain_str}]",
            execution_status=200,
            server="dns_servers",
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
    domain: Annotated[DomainName, Query()],
):
    domain_str = domain.domain
    try:
        await remove_domain_zone_master(domain_str)
        background_tasks.add_task(
            add_action_to_history,
            session=session,
            db_user=current_user,
            action=f"remove dns zone master of domain [{domain_str}]",
            execution_status=200,
            server="dns_servers",
        )
        return Message(message="Zone master deleted successfully")
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
