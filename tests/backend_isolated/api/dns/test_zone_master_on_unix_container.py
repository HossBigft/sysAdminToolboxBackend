# from app.ssh_zone_master import test_zone_master_offline
# from .test_data.hosts import HostList
# import pytest
# from unittest.mock import patch
# from tests.utils.container_unix_utils import UnixContainer
# import pytest_asyncio

# TEST_DNS_HOSTS = ["test"]


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


# @pytest.mark.asyncio
# async def test_get_existing_domain_zone_master_query_on_test_server():
#     test_domain = HostList.CORRECT_EXISTING_DOMAIN
#     result = await test_zone_master_offline(test_domain)

#     expected_result = {
#         "domain": test_domain,
#         "answers": [
#             {"ns": host, "zone_master": "IP_PLACEHOLDER"} for host in TEST_DNS_HOSTS
#         ],
#     }
#     assert result == expected_result


# @pytest.mark.asyncio
# async def test_get_nonexisting_domain_zone_master_query_on_test_server():
#     test_domain = HostList.DOMAIN_WITHOUT_ZONE_MASTER
#     result = await test_zone_master_offline(test_domain)
#     assert result is None
