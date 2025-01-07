from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from typing import Annotated

from app.plesk.ssh_utils import (
    plesk_fetch_subscription_info,
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
    plesk_generate_subscription_login_link,
)
from app.api.dependencies import CurrentUser, SessionDep, RoleChecker
from app.crud import add_dns_set_zone_master_log_entry
from app.plesk.ssh_utils import (
    is_domain_exist_on_server,
    restart_dns_service_for_domain,
)
from app.dns.ssh_utils import dns_remove_domain_zone_master, dns_get_domain_zone_master

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
):
    if not current_user.ssh_username:
        raise HTTPException(
            status_code=404,
            detail=f"User have no Plesk SSH username",
        )
    login_link = await plesk_generate_subscription_login_link(
        PleskServerDomain(domain=data.host),
        data.subscription_id,
        LinuxUsername(name=current_user.ssh_username),
    )

    # background_tasks.add_task(
    #     add_action_to_history,
    #     session=session,
    #     db_user=current_user,
    #     action=f"generate plesk login link for subscription with ID [{data.subscription_id}] on server [{data.host}] for user [{current_user.ssh_username}]",
    #     execution_status="200",
    #     server="dns_servers",
    # )
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
    background_tasks.add_task(
        add_dns_set_zone_master_log_entry,
        session=session,
        db_user=current_user,
        current_zone_master=curr_zone_master,
        target_zone_master=data.target_plesk_server,
        domain=data.domain,
    )
    return Message(message="Zone master set successfully")
