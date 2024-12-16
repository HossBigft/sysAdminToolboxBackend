from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from typing import Annotated

from app.ssh_plesk_subscription_info_retriever import query_subscription_info_by_domain
from app.models import DomainName
from app.models import (
    SubscriptionListResponseModel,
    SubscriptionDetailsModel,
    SubscriptionLoginLinkInput,
    UserRoles,
)
from app.ssh_plesk_login_link_generator import get_plesk_subscription_login_link_by_id
from app.api.dependencies import CurrentUser, SessionDep, RoleChecker
from app.crud import add_action_to_history

router = APIRouter(tags=["plesk"], prefix="/plesk")


@router.get("/get/subscription/", response_model=SubscriptionListResponseModel)
async def find_plesk_subscription_by_domain(
    domain: Annotated[
        DomainName,
        Query(),
    ],
):
    domain_str = domain.domain
    subscriptions = await query_subscription_info_by_domain(domain_str)
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
            domains=[DomainName(domain=d) for d in sub["domains"]],
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
    login_link = await get_plesk_subscription_login_link_by_id(
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
