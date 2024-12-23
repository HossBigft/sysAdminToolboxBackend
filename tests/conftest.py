from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlmodel import Session, delete

from app.core.config import settings
from app.core.db import engine, init_db
from app.main import app
from app.models import User
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers


@pytest_asyncio.fixture(autouse=True)
def mock_ssh_commands(monkeypatch):
    async def mock_execute(*args, **kwargs):
        return ("test-host", "mocked_output", "", 0)

    monkeypatch.setattr("app.ssh_async_executor._run_command_over_ssh", mock_execute)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def db() -> AsyncGenerator[Session, None]:
    with Session(engine) as session:
        init_db(session)
        yield session
        statement = delete(User)
        session.exec(statement)
        session.commit()


@pytest_asyncio.fixture(scope="module")
async def client() -> (
    AsyncGenerator[
        AsyncClient,
        None,
    ]
):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test" + settings.API_V1_STR
    ) as c:
        yield c


@pytest_asyncio.fixture(scope="module")
async def superuser_token_headers(client: AsyncClient) -> dict[str, str]:
    return await get_superuser_token_headers(client)


@pytest_asyncio.fixture(scope="module")
async def normal_user_token_headers(client: AsyncClient, db: Session) -> dict[str, str]:
    return await authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
