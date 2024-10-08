from fastapi import FastAPI
from app.dns_resolver import resolve_record, RecordNotFoundError

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/resolve-a/{domain}")
async def get_a_record(domain: str):
    try:
        a_records = resolve_record(domain, "A")
        return {"domain": domain, "value": a_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/resolve-ptr/{ip}")
async def get_ptr_record(ip: str):
    try:
        ptr_records = resolve_record(ip, "PTR")
        return {"domain": ip, "value": ptr_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/resolve-mx/{domain}")
async def get_mx_record(domain: str):
    try:
        mx_records = resolve_record(domain, "MX")
        return {"domain": domain, "value": mx_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
