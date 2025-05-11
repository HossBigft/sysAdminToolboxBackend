# from fastapi.testclient import TestClient
# from app.main import app
# from .test_data.hosts import HostList
# from unittest.mock import patch
# from tests.core_utils.container_unix_utils import UnixContainer
# import pytest_asyncio
# from app.core.config import settings

# TEST_DNS_HOSTS = ["test"]

# client = TestClient(app)
# client.base_url = str(client.base_url) + settings.API_V1_STR  # adding prefix
# client.base_url = (
#     str(client.base_url).rstrip("/") + "/"
# )  # making sure we have 1 and only 1 `/`


# @pytest_asyncio.fixture(scope="module", autouse=True)
# async def test_container():
#     linux_container = UnixContainer().prepare_zonefile()

#     def mock_batch_ssh(command: str):
#         stdout = linux_container.run_cmd(command)
#         return [{"host": "test", "stdout": stdout}]

#     with patch(
#         "app.ssh_zone_master.batch_ssh_execute",
#         wraps=mock_batch_ssh,
#     ):
#         yield linux_container


# def test_zonemaster_resolution_with_nonexisting_domain(
#     domain=HostList.DOMAIN_WITHOUT_ZONE_MASTER,
# ):
#     response = client.get(f"/dns/internal/zonemaster/?domain={domain}")
#     assert response.status_code == 404


# def test_zonemaster_resolution_with_existing_domain(
#     domain=HostList.CORRECT_EXISTING_DOMAIN,
# ):
#     expected_result = {
#         "domain": domain,
#         "answers": [
#             {"ns": host, "zone_master": "IP_PLACEHOLDER"} for host in TEST_DNS_HOSTS
#         ],
#     }
#     response = client.get(f"/dns/internal/zonemaster/?domain={domain}")
#     assert response.status_code == 200
#     assert response.json() == expected_result
