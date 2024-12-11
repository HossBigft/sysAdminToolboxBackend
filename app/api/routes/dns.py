from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic.networks import IPvAnyAddress
from app.ssh_zone_master import getDomainZoneMaster
from app.dns_resolver import resolve_record, RecordNotFoundError
from app.validators import validate_domain_name
from app.crud import add_action_to_history
from app.api.dependencies import CurrentUser, SessionDep, RoleChecker
from app.models import UserRoles

router = APIRouter(tags=["dns"], prefix="/dns")


@router.get("/internal/resolve/a/")
async def get_a_record(domain: str = Depends(validate_domain_name)):
    try:
        a_records = resolve_record(domain, "A")
        return {"domain": domain, "records": a_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/resolve/ptr/")
async def get_ptr_record(
    ip: IPvAnyAddress,
):
    try:
        ptr_records = resolve_record(str(ip), "PTR")
        return {"ip": ip, "records": ptr_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/internal/get/zonemaster/",
    dependencies=[Depends(RoleChecker([UserRoles.SUPERUSER, UserRoles.ADMIN]))],
)
async def get_zone_master_from_dns_servers(
    session: SessionDep,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    domain: str = Depends(validate_domain_name),
):
    try:
        zone_masters_dict = await getDomainZoneMaster(domain)
        if not zone_masters_dict:
            background_tasks.add_task(
                add_action_to_history(
                    session=session,
                    db_user=current_user,
                    action=f"get zonemaster of domain [{domain}]",
                    execution_status=404,
                    server="dns_servers",
                )
            )
            raise HTTPException(
                status_code=404, detail=f"Zone master for domain [{domain}] not found."
            )
        background_tasks.add_task(
            add_action_to_history(
                session=session,
                db_user=current_user,
                action=f"get zonemaster of domain [{domain}]",
                execution_status=200,
                server="dns_servers",
            )
        )
        return zone_masters_dict
    except RecordNotFoundError as e:
        background_tasks.add_task(
            add_action_to_history(
                session=session,
                db_user=current_user,
                action=f"get zonemaster of domain [{domain}]",
                execution_status=404,
                server="dns_servers",
            )
        )
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/internal/resolve/mx/")
async def get_mx_record(domain: str = Depends(validate_domain_name)):
    try:
        mx_records = resolve_record(domain, "MX")
        return {"domain": domain, "records": mx_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/resolve/ns/")
async def get_ns_records(domain: str = Depends(validate_domain_name)):
    try:
        ns_records = resolve_record(domain, "NS")
        return {"domain": domain, "records": ns_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
