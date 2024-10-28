import pytest
from tests.utils.db_utils import populate_test_db, cleanup_test_db, TEST_DB_CMD
from tests.test_data.hosts import HostList
from unittest.mock import patch
from app.ssh_plesk_subscription_info_retriever import query_domain_info


@pytest.fixture(scope="class", autouse=True)
def init_test_db():
    populate_test_db()
    yield
    cleanup_test_db()


@pytest.mark.asyncio
async def test_get_existing_subscription_info():
    test_domain = HostList.CORRECT_EXISTING_DOMAIN
    test_server = [HostList.SSH_TEST_SERVER]
    with patch(
        "app.ssh_plesk_subscription_info_retriever.PLESK_SERVER_LIST", test_server
    ):
        with patch(
            "app.ssh_plesk_subscription_info_retriever.PLESK_DB_RUN_CMD", TEST_DB_CMD
        ):
            result = await query_domain_info(test_domain, verbose_flag=True)
    expected_output = [
        {
            "host": HostList.SSH_TEST_SERVER,
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
