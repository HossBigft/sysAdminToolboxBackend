import pytest
from app.ssh_plesk_subscription_info_retriever import query_domain_info
from tests.utils.container_db_utils import TestMariadb, TEST_DB_CMD
from tests.test_data.hosts import HostList
from unittest.mock import patch

@pytest.fixture(scope="class")
def init_test_db():
    testdb = TestMariadb().populate_db()

    def mock_batch_ssh(command: str):
        stdout = testdb.run_cmd(command)
        return [{"host": "test", "stdout": stdout}]

    with patch("app.ssh_plesk_subscription_info_retriever.PLESK_DB_RUN_CMD", TEST_DB_CMD):
        with patch("app.ssh_plesk_subscription_info_retriever.batch_ssh_execute", wraps=mock_batch_ssh):
            yield testdb  # Yield the test database for use in tests


@pytest.mark.asyncio
async def test_get_existing_subscription_info(init_test_db):
    result = await query_domain_info(HostList.CORRECT_EXISTING_DOMAIN)

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
            ],
        }
    ]

    assert result == expected_output


@pytest.mark.asyncio
async def test_get_nonexisting_subscription_info(init_test_db):
    result = await query_domain_info("zless.kz")

    expected_output = []

    assert result == expected_output
