from fastapi import FastAPI, HTTPException, Path
from app.dns_resolver import resolve_record, RecordNotFoundError
import uvicorn
from typing import Annotated

DOMAIN_REGEX_PATTERN = (
    "^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$"
)

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/resolve-a/{domain}")
async def get_a_record(domain: Annotated[str, Path(max_length=63, regex=DOMAIN_REGEX_PATTERN)]):
    try:
        a_records = resolve_record(domain, "A")
        return {"domain": domain, "value": a_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/resolve-ptr/{ip}")
async def get_ptr_record(ip: str):
    try:
        print(f"IP {ip}")
        ptr_records = resolve_record(str(ip), "PTR")
        return {"ip": ip, "value": ptr_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/resolve-mx/{domain}")
async def get_mx_record(domain: Annotated[str, Path(max_length=63, regex=DOMAIN_REGEX_PATTERN)]):
    try:
        mx_records = resolve_record(domain, "MX")
        return {"domain": domain, "value": mx_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="IP_PLACEHOLDER", port=5000, log_level="debug")
