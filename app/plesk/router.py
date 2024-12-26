from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from typing import Annotated

from app.plesk.ssh_utils import (
    fetch_subscription_info,
)
from app.plesk.models import (
    SubscriptionListResponseModel,
    SubscriptionDetailsModel,
    SubscriptionLoginLinkInput,
    SubscriptionName,
    DomainName,
    SetZonemasterInput,
)
from app.models import UserRoles, Message
from app.plesk.ssh_utils import (
    generate_subscription_login_link,
)
from app.api.dependencies import CurrentUser, SessionDep, RoleChecker
from app.crud import add_action_to_history
from app.plesk.ssh_utils import (
    is_domain_exist_on_server,
    restart_dns_service_for_domain,
)
from app.dns.ssh_utils import remove_domain_zone_master

router = APIRouter(tags=["plesk"], prefix="/plesk")


@router.get("/get/subscription/", response_model=SubscriptionListResponseModel)
async def find_plesk_subscription_by_domain(
    domain: Annotated[
        SubscriptionName,
        Query(),
    ],
):
    domain_str = domain.domain
    subscriptions = await fetch_subscription_info(domain_str)
    if not subscriptions:
        raise HTTPException(
            status_code=404,
            detail=f"Subscription with domain [{domain_str}] not found.",
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
        data.host, data.subscription_id, current_user.ssh_username
    )

    background_tasks.add_task(
        add_action_to_history,
        session=session,
        db_user=current_user,
        action=f"generate plesk login link for subscription with ID [{data.subscription_id}] on server [{data.host}] for user [{current_user.ssh_username}]",
        execution_status=200,
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
    if await is_domain_exist_on_server(data.target_plesk_server, data.domain):
        await remove_domain_zone_master(domain_name=data.domain)
        await restart_dns_service_for_domain(
            host=data.target_plesk_server, domain=data.domain
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
        action=f"restart dns service for domain [{data.domain}] on server [{data.target_plesk_server}]",
        execution_status=200,
        server="plesk_servers",
    )
    return Message(message="Zone master set successfully")
