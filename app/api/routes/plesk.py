from fastapi import APIRouter, HTTPException, Query
from app.ssh_plesk_subscription_info_retriever import query_subscription_info_by_domain
from app.models import Domain
from app.models import SubscriptionInfoResponseModel, SubscriptionInfoModel
from typing import Annotated

router = APIRouter(tags=["plesk"], prefix="/plesk")


@router.get("/get/subscription/", response_model=SubscriptionInfoResponseModel)
async def find_plesk_subscription_by_domain(
    domain: Annotated[
        Domain,
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
        SubscriptionInfoModel(
            host=Domain(domain=sub["host"]),
            id=sub["id"],
            name=sub["name"],
            username=sub["username"],
            userlogin=sub["userlogin"],
            domains=[Domain(domain=d) for d in sub["domains"]],
        )
        for sub in subscriptions
    ]

    return SubscriptionInfoResponseModel(root=subscription_models)
