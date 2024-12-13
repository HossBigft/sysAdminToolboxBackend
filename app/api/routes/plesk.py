from fastapi import APIRouter, HTTPException, Query
from app.ssh_plesk_subscription_info_retriever import query_subscription_info_by_domain
from app.models import DomainModel
from app.models import SubscriptionInfoResponseModel
from typing import Annotated

router = APIRouter(tags=["plesk"], prefix="/plesk")


@router.get("/get/subscription/", response_model=SubscriptionInfoResponseModel)
async def find_plesk_subscription_by_domain(
    domain: Annotated[DomainModel, Query()],
):
    domain_str = domain.domain
    subscriptions = await query_subscription_info_by_domain(domain_str)
    if not subscriptions:
        raise HTTPException(
            status_code=404,
            detail=f"Subscription with domain [{domain_str}] not found.",
        )
    return subscriptions
