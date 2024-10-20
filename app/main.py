from fastapi import FastAPI, HTTPException, Query, Depends
from .dns_resolver import resolve_record, RecordNotFoundError
import uvicorn
from typing import Annotated
from pydantic.networks import IPvAnyAddress
from .ssh_zone_master import getDomainZoneMasterAsync
from .ssh_plesk_subscription_info_retriever import query_domain_info
from .plesk_queries import send_hello


DOMAIN_REGEX_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$"
)


def validate_domain_name(
    domain: Annotated[
        str, Query(min_length=3, max_length=63, pattern=DOMAIN_REGEX_PATTERN)
    ],
):
    return domain


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/resolve/a/")
async def get_a_record(domain: str = Depends(validate_domain_name)):
    try:
        a_records = resolve_record(domain, "A")
        return {"domain": domain, "value": a_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/resolve/ptr/")
async def get_ptr_record(
    ip: IPvAnyAddress,
):
    try:
        ptr_records = resolve_record(str(ip), "PTR")
        return {"ip": ip, "value": ptr_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/resolve/mx/")
async def get_mx_record(domain: str = Depends(validate_domain_name)):
    try:
        mx_records = resolve_record(domain, "MX")
        return {"domain": domain, "value": mx_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/plesk/greet")
async def get_answers_from_plesk_servers():
    try:
        return await send_hello()

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/resolve/zonemaster/")
async def get_zone_master_from_dns_servers(domain: str = Depends(validate_domain_name)):
    try:
        zone_masters_dict = await getDomainZoneMasterAsync(domain)
        return zone_masters_dict
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/plesk/get/subscription/")
async def find_plesk_subscription_by_domain(
    domain: str = Depends(validate_domain_name),
):
    try:
        subscriptions = await query_domain_info(domain)
        return subscriptions
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="IP_PLACEHOLDER", port=5000, log_level="debug")
