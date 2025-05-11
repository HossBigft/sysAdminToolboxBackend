from fastapi import APIRouter

router = APIRouter(tags=["core_utils"], prefix="/core_utils")


@router.get("/health-check/")
async def health_check() -> bool:
    return True
