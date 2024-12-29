from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from typing import Annotated

from app.plesk.ssh_utils import (
    fetch_subscription_info,
)
from app.plesk.models import (
    SubscriptionListResponseModel,
    SubscriptionDetailsModel,
    SubscriptionLoginLinkInput,
    DomainName,
    SetZonemasterInput,
    LinuxUsername,
    PleskServerDomain,
)
from app.models import UserRoles, Message, SubscriptionName
from app.plesk.ssh_utils import (
    generate_subscription_login_link,
)
from app.api.dependencies import CurrentUser, SessionDep, RoleChecker
from app.crud import add_action_to_history
from app.plesk.ssh_utils import (
    is_domain_exist_on_server,
    restart_dns_service_for_domain,
)
from app.dns.ssh_utils import remove_domain_zone_master, get_domain_zone_master

router = APIRouter(tags=["plesk"], prefix="/plesk")


@router.get("/get/subscription/", response_model=SubscriptionListResponseModel)
async def find_plesk_subscription_by_domain(
    domain: Annotated[
        SubscriptionName,
        Query(),
    ],
) -> SubscriptionListResponseModel:
    subscriptions = await fetch_subscription_info(domain)
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
):
    login_link = await generate_subscription_login_link(
        PleskServerDomain(domain=data.host),
        data.subscription_id,
        LinuxUsername(name=current_user.ssh_username),
    )

    background_tasks.add_task(
        add_action_to_history,
        session=session,
        db_user=current_user,
        action=f"generate plesk login link for subscription with ID [{data.subscription_id}] on server [{data.host}] for user [{current_user.ssh_username}]",
        execution_status="200",
        server="dns_servers",
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
) -> Message:
    curr_zonemaster: set[PleskServerDomain]
    if await is_domain_exist_on_server(
        host=PleskServerDomain(domain=data.target_plesk_server),
        domain=SubscriptionName(domain=data.domain),
    ):
        curr_zonemaster = await get_domain_zone_master(
            SubscriptionName(domain=data.domain)
        )
        await remove_domain_zone_master(SubscriptionName(domain=data.domain))
        await restart_dns_service_for_domain(
            host=PleskServerDomain(domain=data.target_plesk_server),
            domain=SubscriptionName(domain=data.domain),
        )
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Subscription with domain [{data.domain}] not found.",
        )
    background_tasks.add_task(
        add_action_to_history,
        session=session,
        db_user=current_user,
        action=f"Set zonemaster for domain [{data.domain}] [{curr_zonemaster}->{data.target_plesk_server}]",
        execution_status="200",
        server="plesk_servers",
    )
    return Message(message="Zone master set successfully")
