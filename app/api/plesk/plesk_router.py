from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks, Request
from typing import Annotated

from app.api.plesk.ssh_utils import (
    plesk_fetch_subscription_info,
)
from app.api.plesk.plesk_schemas import (
    SubscriptionListResponseModel,
    SubscriptionDetailsModel,
    SubscriptionLoginLinkInput,
    SetZonemasterInput,
    LinuxUsername,
)
from app.schemas import (
    UserRoles,
    Message,
    SubscriptionName,
    DomainName,
    PleskServerDomain,
    IPv4Address,
)
from app.api.plesk.ssh_utils import (
    plesk_generate_subscription_login_link,
)
from app.api.dependencies import CurrentUser, SessionDep, RoleChecker
from app.api.plesk.ssh_utils import (
    is_domain_exist_on_server,
    restart_dns_service_for_domain,
)
from app.api.dns.ssh_utils import (
    dns_remove_domain_zone_master,
    dns_get_domain_zone_master,
)
from app.db.crud import (
    log_dns_zone_master_set,
    log_plesk_login_link_get,
)

router = APIRouter(tags=["plesk"], prefix="/plesk")


@router.get("/get/subscription/", response_model=SubscriptionListResponseModel)
async def find_plesk_subscription_by_domain(
    domain: Annotated[
        SubscriptionName,
        Query(),
    ],
) -> SubscriptionListResponseModel:
    subscriptions = await plesk_fetch_subscription_info(domain)
    if not subscriptions:
        raise HTTPException(
            status_code=404,
            detail=f"Subscription with domain [{domain.domain}] not found.",
        )
    subscription_models = [
        SubscriptionDetailsModel(
            host=DomainName(domain=sub["host"]),
            id=sub["id"],
            name=sub["name"],
            username=sub["username"],
            userlogin=sub["userlogin"],
            domains=[SubscriptionName(domain=d) for d in sub["domains"]],
        )
        for sub in subscriptions
    ]

    return SubscriptionListResponseModel(root=subscription_models)


@router.post(
    "/subscription/login-link",
    dependencies=[Depends(RoleChecker([UserRoles.SUPERUSER, UserRoles.ADMIN]))],
)
async def get_subscription_login_link(
    data: SubscriptionLoginLinkInput,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    request: Request,
):
    if not current_user.ssh_username:
        raise HTTPException(
            status_code=404,
            detail="User have no Plesk SSH username",
        )
    login_link = await plesk_generate_subscription_login_link(
        PleskServerDomain(domain=data.host),
        data.subscription_id,
        LinuxUsername(name=current_user.ssh_username),
    )
    request_ip = IPv4Address(ip=request.client.host)
    background_tasks.add_task(
        log_plesk_login_link_get,
        session=session,
        user=current_user,
        plesk_server=PleskServerDomain(domain=data.host),
        subscription_id=data.subscription_id,
        ip=request_ip,
    )
    return login_link


@router.post(
    "/zonemaster/set",
    dependencies=[Depends(RoleChecker([UserRoles.SUPERUSER, UserRoles.ADMIN]))],
)
async def set_zonemaster(
    data: SetZonemasterInput,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    request: Request,
) -> Message:
    curr_zone_master: set[PleskServerDomain] | None
    if await is_domain_exist_on_server(
        host=PleskServerDomain(domain=data.target_plesk_server),
        domain=SubscriptionName(domain=data.domain),
    ):
        curr_zone_master = await dns_get_domain_zone_master(
            SubscriptionName(domain=data.domain)
        )

        await dns_remove_domain_zone_master(SubscriptionName(domain=data.domain))
        await restart_dns_service_for_domain(
            host=PleskServerDomain(domain=data.target_plesk_server),
            domain=SubscriptionName(domain=data.domain),
        )
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Subscription with domain [{data.domain}] not found.",
        )
    request_ip = IPv4Address(ip=request.client.host)
    background_tasks.add_task(
        log_dns_zone_master_set,
        session=session,
        user=current_user,
        current_zone_master=curr_zone_master,
        target_zone_master=PleskServerDomain(domain=data.target_plesk_server),
        domain=DomainName(domain=data.domain),
        ip=request_ip,
    )
    return Message(message="Zone master set successfully")
