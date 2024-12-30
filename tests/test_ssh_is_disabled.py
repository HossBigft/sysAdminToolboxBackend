import pytest
from app.AsyncSSHandler import execute_ssh_commands_in_batch
from app.host_lists import PLESK_SERVER_LIST
from tests.conftest import MOCK_SSH_COMMAND_RESULT


@pytest.mark.asyncio
async def test_ssh_is_disabled() -> None:
    results = await execute_ssh_commands_in_batch(
        server_list=PLESK_SERVER_LIST, command="echo ok", verbose=True
    )
    assert all(item == MOCK_SSH_COMMAND_RESULT for item in results)
