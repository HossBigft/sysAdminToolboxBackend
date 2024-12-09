import logging
from app.api.routes import login, dns, users, plesk, utils
from fastapi import APIRouter


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("actions.log"),  # Save logs to app.log
        logging.StreamHandler(),  # Also log to console
    ],
)

logger = logging.getLogger(__name__)


api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(dns.router)
api_router.include_router(users.router)
api_router.include_router(plesk.router)
api_router.include_router(utils.router)
