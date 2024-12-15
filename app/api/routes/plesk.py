from fastapi import APIRouter, HTTPException, Query
from app.ssh_plesk_subscription_info_retriever import query_subscription_info_by_domain
from app.models import DomainName
from app.models import SubscriptionListResponseModel, SubscriptionDetailsModel
from typing import Annotated

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
