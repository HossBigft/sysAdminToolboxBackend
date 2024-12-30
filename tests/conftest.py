from collections.abc import AsyncGenerator

import pytest_asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from sqlmodel import Session, delete

from app.core.config import settings
from app.core.db import engine, init_db
from app.main import app
from app.models import User
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers

MOCK_SSH_COMMAND_RESULT = {
    "host": "mocked_host",
    "stdout": "mocked_stdout",
    "stderr": "",
    "returncode": 0,
}


@pytest_asyncio.fixture(autouse=True)
def mock_ssh_commands(monkeypatch):
    """Mock the `_execute_ssh_command` function."""

    async def mock_execute_ssh_command(host, command, verbose):
        return MOCK_SSH_COMMAND_RESULT

    monkeypatch.setattr(
        "app.AsyncSSHandler._execute_ssh_command", mock_execute_ssh_command
    )


@pytest_asyncio.fixture(autouse=True)
async def validate_ssh_disabled():
    """Ensure SSH is disabled before running tests."""
    from app.AsyncSSHandler import execute_ssh_commands_in_batch
    from app.host_lists import PLESK_SERVER_LIST

    results = await execute_ssh_commands_in_batch(
        server_list=PLESK_SERVER_LIST, command="echo ok", verbose=True
    )
    print("SSH Command Results:", results)
    if not all(result == MOCK_SSH_COMMAND_RESULT for result in results):
        pytest.exit("SSH is not disabled, skipping all tests.")


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
