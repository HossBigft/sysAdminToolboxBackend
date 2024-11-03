from fastapi import FastAPI, HTTPException, Query, Depends, Request, Response
from .dns_resolver import resolve_record, RecordNotFoundError
import uvicorn
from typing import Annotated
from pydantic.networks import IPvAnyAddress
from .ssh_zone_master import getDomainZoneMaster
from .ssh_plesk_subscription_info_retriever import query_subscription_info_by_domain
import logging
import time
from app.routes import login

DOMAIN_REGEX_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$"
)


async def validate_domain_name(
    domain: Annotated[
        str, Query(min_length=3, max_length=63, pattern=DOMAIN_REGEX_PATTERN)
    ],
):
    return domain


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


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/dns/resolve/a/")
async def get_a_record(domain: str = Depends(validate_domain_name)):
    try:
        a_records = resolve_record(domain, "A")
        return {"domain": domain, "records": a_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/dns/resolve/ptr/")
async def get_ptr_record(
    ip: IPvAnyAddress,
):
    try:
        ptr_records = resolve_record(str(ip), "PTR")
        return {"ip": ip, "records": ptr_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/dns/get/zonemaster/")
async def get_zone_master_from_dns_servers(domain: str = Depends(validate_domain_name)):
    try:
        zone_masters_dict = await getDomainZoneMaster(domain)
        if not zone_masters_dict:
            return Response(status_code=204)
        return zone_masters_dict
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/plesk/get/subscription/")
async def find_plesk_subscription_by_domain(
    domain: str = Depends(validate_domain_name),
):
        subscriptions = await query_subscription_info_by_domain(domain)
        if not subscriptions:
            return Response(status_code=204)
        return subscriptions

@app.get("/dns/resolve/mx/")
async def get_mx_record(domain: str = Depends(validate_domain_name)):
    try:
        mx_records = resolve_record(domain, "MX")
        return {"domain": domain, "records": mx_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/dns/resolve/ns/")
async def get_ns_records(domain: str = Depends(validate_domain_name)):
    try:
        ns_records = resolve_record(domain, "NS")
        return {"domain": domain, "records": ns_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


app.include_router(login.router, tags=["login"])
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", host="IP_PLACEHOLDER", port=5000, log_level="debug", reload=True
    )
