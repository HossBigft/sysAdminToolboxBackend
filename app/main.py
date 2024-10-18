from fastapi import FastAPI, HTTPException, Path, Query
from app.dns_resolver import resolve_record, RecordNotFoundError
import uvicorn
from typing import Annotated
from pydantic.networks import IPvAnyAddress
from app import  getDomainZoneMaster
from .plesk_queries import send_hello


DOMAIN_REGEX_PATTERN = (
    r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$"
)

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/resolve/a/")
async def get_a_record(
    domain: Annotated[str, Query(max_length=63, pattern=DOMAIN_REGEX_PATTERN)],
):
    try:
        a_records = resolve_record(domain, "A")
        return {"domain": domain, "value": a_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/resolve-ptr/{ip}")
async def get_ptr_record(
    ip: IPvAnyAddress,
):
    try:
        ptr_records = resolve_record(str(ip), "PTR")
        return {"ip": ip, "value": ptr_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/resolve-mx/{domain}")
async def get_mx_record(
    domain: Annotated[str, Path(max_length=63, pattern=DOMAIN_REGEX_PATTERN)],
):
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
async def get_zone_master_from_dns_servers(
    domain_name: Annotated[str, Query(min_length=3,max_length=63, pattern=DOMAIN_REGEX_PATTERN)],
):
    try:
        zone_masters_dict = getDomainZoneMaster(domain_name)
        return zone_masters_dict
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="IP_PLACEHOLDER", port=5000, log_level="debug")
