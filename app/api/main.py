from fastapi import HTTPException, Depends, Request
from fastapi.responses import RedirectResponse, Response
from app.ssh_plesk_subscription_info_retriever import query_subscription_info_by_domain
import logging
import time
from app.api.routes import login, dns
from app.validators import validate_domain_name
from fastapi import APIRouter

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("actions.log"),  # Save logs to app.log
        logging.StreamHandler(),  # Also log to console
    ],
)

logger = logging.getLogger(__name__)

# dummy tag to make apirouter index out of range go away
api_router = APIRouter(tags=["main"])


# @api_router.middleware("http")
# async def log_requests(request: Request, call_next):
#     start_time = time.time()

#     # Log request details
#     logger.info(f"Request: {request.method} {request.url}")

#     # Process the request
#     response: Response = await call_next(request)

#     # Log response details
#     duration = time.time() - start_time
#     logger.info(f"Response: {response.status_code} - Duration: {duration:.4f}s")

#     return response


@api_router.get("/", include_in_schema=False)
async def redirect_to_docs():
    response = RedirectResponse(url="/docs")
    return response


@api_router.get("/plesk/get/subscription/")
async def find_plesk_subscription_by_domain(
    domain: str = Depends(validate_domain_name),
):
    subscriptions = await query_subscription_info_by_domain(domain)
    if not subscriptions:
        raise HTTPException(
            status_code=404, detail=f"Subscription with domain [{domain}] not found."
        )
    return subscriptions


@api_router.get("/health-check/")
async def health_check() -> bool:
    return True


api_router.include_router(login.router, tags=["login"])
api_router.include_router(dns.router, tags=["dns"])
