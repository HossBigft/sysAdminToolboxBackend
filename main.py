from fastapi import FastAPI
from pFindPleskHostByDomain import resolve_a_record, RecordNotFoundError

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/resolve-a-record/{domain}")
async def get_a_record(domain: str):
    try:
        a_records = resolve_a_record(domain)
        return {"domain": domain, "A_records": a_records}
    except RecordNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
