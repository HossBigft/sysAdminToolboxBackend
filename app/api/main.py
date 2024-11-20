import logging
from app.api.routes import login, dns, users, plesk, utils
from fastapi import APIRouter

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

# dummy tag to make apirouter index out of range go away



# @api_router.middleware("http")
# async def log_requests(request: Request, call_next):
#     start_time = time.time()

#     # Log request details
#     logger.info(f"Request: {request.method} {request.url}")

#     # Process the request
#     response: Response = await call_next(request)

#     # Log response details
#     duration = time.time() - start_time
#     logger.info(f"Response: {response.status_code} - Duration: {duration:.4f}s")

#     return response


api_router = APIRouter()
api_router.include_router(login.router, tags=["login"])
api_router.include_router(dns.router, tags=["dns"])
api_router.include_router(users.router, tags=["users"])
api_router.include_router(plesk.router, tags=["plesk"])
api_router.include_router(utils.router, tags=["utils"])



