from fastapi import APIRouter

PREFIX = "/utils"

router = APIRouter(prefix=PREFIX)

@router.get("/health-check/")
async def health_check() -> bool:
    return True