import pytest
from app.api.plesk.ssh_utils import (
    plesk_fetch_subscription_info,
)
from tests.utils.container_db_utils import TestMariadb, TEST_DB_CMD
from tests.test_data.hosts import HostList
from unittest.mock import patch
from app.schemas import SubscriptionName

@pytest.fixture(scope="module")
def init_test_db():
    testdb = TestMariadb().populate_db()

    def mock_batch_ssh(command: str):
        stdout = testdb.run_cmd(command)
        return [{"host": "test", "stdout": stdout}]

    with patch("app.api.plesk.ssh_utils.PLESK_DB_RUN_CMD_TEMPLATE", TEST_DB_CMD):
        with patch(
            "app.api.plesk.ssh_utils.batch_ssh_execute",
            wraps=mock_batch_ssh,
        ):
            yield testdb  # Yield the test database for use in tests


@pytest.mark.asyncio
async def test_get_existing_subscription_info(init_test_db):
    result = await plesk_fetch_subscription_info(SubscriptionName(name=HostList.CORRECT_EXISTING_DOMAIN))

    expected_output = [
        {
            "host": "test",
            "id": "1184",
google.com
            "username": "FIO",
            "userlogin": "p-2342343",
            "domains": [
google.com
google.com
google.com
google.com
google.com
google.com
google.com
google.com
google.com
google.com
            ],
        }
    ]

    assert result == expected_output


@pytest.mark.asyncio
async def test_get_nonexisting_subscription_info(init_test_db):
    result = await plesk_fetch_subscription_info(SubscriptionName(name="zless.kz"))
    assert result is None
