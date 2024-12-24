import logging
from app.api.routes import dns, users, utils, password_reset
from fastapi import APIRouter

from app.auth import router as login
from app.plesk import router as plesk


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
api_router.include_router(password_reset.router)
