from unittest.mock import patch, AsyncMock
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.main import api_router
from app.core.config import settings
from tests.utils.container_db_utils import TestMariadb, TEST_DB_CMD
from tests.utils.container_unix_utils import UnixContainer
from app.schemas import PleskServerDomain
from app.core_utils.loggers import disable_default_uvicorn_access_logs, setup_actions_logger

TEST_SSH_HOST = "plesk.example.com"


# Custom unique ID generator function for routes
def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


# Initialize Sentry SDK if not in local environment
if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    import sentry_sdk

    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    disable_default_uvicorn_access_logs()
    setup_actions_logger()
    yield
# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

# Set up CORS middleware if configured
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


testdb = TestMariadb().populate_db()
linux_container = UnixContainer().prepare_zonefile()


def mock_batch_ssh(command: str):
    stdout = testdb.run_cmd(command)
    
    return [{"host": TEST_SSH_HOST, "stdout": stdout}]


def mock_batch_ssh_ns(command: str):
    stdout = linux_container.run_cmd(command)
    return [{"host": TEST_SSH_HOST, "stdout": stdout}]


def mock_get_plesk_subscription_login_link_by_id(arg1, arg2, arg3):
    return f"https://{TEST_SSH_HOST}/login?secret=sdfdfsdfSECRET&success_redirect_url=%2Fadmin%2Fsubscription%2Foverview%2Fid%2F12345"


def mock_dns_get_domain_zone_master(domain: str):
    return PleskServerDomain(name=TEST_SSH_HOST)


get_zone_master_patches = [
    patch("app.api.plesk.ssh_utils.PLESK_DB_RUN_CMD_TEMPLATE", TEST_DB_CMD),
    patch(
        "app.api.plesk.ssh_utils.batch_ssh_execute",
        wraps=mock_batch_ssh,
    ),
    patch("app.api.dns.ssh_utils.batch_ssh_execute", wraps=mock_batch_ssh_ns),
]
set_zone_master_patches = [
    patch(
        "app.api.plesk.plesk_router.is_domain_exist_on_server",
        wraps=AsyncMock(return_value=True),
    ),
    patch(
        "app.api.plesk.plesk_router.dns_get_domain_zone_master",
        wraps=mock_dns_get_domain_zone_master,
    ),
    patch(
        "app.api.plesk.plesk_router.dns_remove_domain_zone_master", wraps=AsyncMock()
    ),
    patch(
        "app.api.plesk.plesk_router.restart_dns_service_for_domain", wraps=AsyncMock()
    ),
]
patches = (
    [
        patch(
            "app.api.plesk.plesk_router.plesk_generate_subscription_login_link",
            wraps=mock_get_plesk_subscription_login_link_by_id,
        )
    ]
    + get_zone_master_patches
    + set_zone_master_patches
)

for p in patches:
    p.start()

# Include API router
app.include_router(api_router)
