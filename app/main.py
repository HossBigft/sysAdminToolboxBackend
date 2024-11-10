from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse, Response
import uvicorn
from .ssh_plesk_subscription_info_retriever import query_subscription_info_by_domain
import logging
import time
from app.routes import login, dns
from app.validators import validate_domain_name

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

app = FastAPI()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Log request details
    logger.info(f"Request: {request.method} {request.url}")

    # Process the request
    response: Response = await call_next(request)

    # Log response details
    duration = time.time() - start_time
    logger.info(f"Response: {response.status_code} - Duration: {duration:.4f}s")

    return response


@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    response = RedirectResponse(url="/docs")
    return response


@app.get("/plesk/get/subscription/")
async def find_plesk_subscription_by_domain(
    domain: str = Depends(validate_domain_name),
):
    subscriptions = await query_subscription_info_by_domain(domain)
    if not subscriptions:
        raise HTTPException(
            status_code=404, detail=f"Subscription with domain [{domain}] not found."
        )
    return subscriptions


@app.get("/health-check/")
async def health_check() -> bool:
    return True


app.include_router(login.router, tags=["login"])
app.include_router(dns.router, tags=["dns"])
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", host="IP_PLACEHOLDER", port=5000, log_level="debug", reload=True
    )
