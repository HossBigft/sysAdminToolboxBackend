import sentry_sdk

from fastapi import FastAPI, APIRouter
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core_utils.loggers import LoggingMiddleware
from app.core_utils.ssh_multiplexing_warmup import ssh_multiplexing_warmup
from app.users import users_router as users
from app.auth import auth_router as login, password_reset
from app.api import utils_router as utils, plesk_router as plesk, dns_router as dns
from app.core_utils.loggers import disable_default_uvicorn_access_logs, setup_actions_logger, setup_custom_access_logger, setup_ssh_logger


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    disable_default_uvicorn_access_logs()
    setup_custom_access_logger()
    setup_actions_logger()
    setup_ssh_logger()
    # await ssh_multiplexing_warmup()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(LoggingMiddleware)
api_router = APIRouter(prefix=settings.API_V1_STR)

api_router.include_router(dns.router)
api_router.include_router(users.router)
api_router.include_router(plesk.router)
api_router.include_router(utils.router)
api_router.include_router(password_reset.router)
api_router.include_router(login.router)

app.include_router(api_router)
