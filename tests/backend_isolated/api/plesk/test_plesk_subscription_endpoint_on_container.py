from fastapi.testclient import TestClient
from app.main import app
from tests.test_data.hosts import HostList
import pytest
from unittest.mock import patch
from tests.utils.container_db_utils import TestMariadb, TEST_DB_CMD
import pytest_asyncio
from app.core.config import settings

TEST_HOSTS = ["test.com"]


client = TestClient(app)
client.base_url = str(client.base_url) + settings.API_V1_STR  # adding prefix
client.base_url = (
    str(client.base_url).rstrip("/") + "/"
)  # making sure we have 1 and only 1 `/`


@pytest_asyncio.fixture(scope="module", autouse=True)
async def test_container():
    testdb = TestMariadb().populate_db()

    def mock_batch_ssh(command: str):
        stdout = testdb.run_cmd(command)
        return [{"host": TEST_HOSTS[0], "stdout": stdout}]

    with patch(
        "app.plesk.ssh_plesk_subscription_info_retriever.PLESK_DB_RUN_CMD", TEST_DB_CMD
    ):
        with patch(
            "app.plesk.ssh_plesk_subscription_info_retriever.batch_ssh_execute",
            wraps=mock_batch_ssh,
        ):
            yield testdb  # Yield the test database for use in tests


def test_subscription_info_retrieval_with_existing_domain(
    domain=HostList.CORRECT_EXISTING_DOMAIN,
):
    expected_result = [
        {
            "host": TEST_HOSTS[0],
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
    response = client.get(f"/plesk/get/subscription/?domain={domain}")
    assert response.status_code == 200
    assert response.json() == expected_result


@pytest.mark.asyncio
async def test_subscription_info_retrieval_with_nonexistant_domain(
    domain="asdasd.kz",
):
    response = client.get(f"/plesk/get/subscription/?domain={domain}")
    print(response)
    assert response.status_code == 404
