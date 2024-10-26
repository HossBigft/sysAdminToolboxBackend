from app.ssh_zone_master import getDomainZoneMaster
from .test_data.hosts import HostList
import pytest
from unittest.mock import patch
from tests.utils.ssh_utils import prepare_zonefile, TEST_ZONE_FILE_PATH
import pytest_asyncio


@pytest_asyncio.fixture(scope="module", autouse=True)
async def prepare_zonemaster_test():
    await prepare_zonefile()


@pytest.mark.asyncio
async def test_get_existing_domain_zone_master_query_on_test_server():
    test_domain = HostList.CORRECT_EXISTING_DOMAIN
    test_dns_servers = [HostList.SSH_TEST_SERVER]
    with patch("app.ssh_zone_master.ZONEFILE_PATH", TEST_ZONE_FILE_PATH):
        with patch("app.ssh_zone_master.DNS_SERVER_LIST", test_dns_servers):
            result = await getDomainZoneMaster(test_domain, debug_flag=True)

            expected_result = {
                "domain": test_domain,
                "answers": [
                    {"ns": host, "zone_master": "IP_PLACEHOLDER"}
                    for host in test_dns_servers
                ],
            }
            assert result == expected_result


@pytest.mark.asyncio
async def test_get_nonexisting_domain_zone_master_query_on_test_server():
    test_domain = HostList.DOMAIN_WITHOUT_ZONE_MASTER
    test_dns_servers = [HostList.SSH_TEST_SERVER]
    with patch("app.ssh_zone_master.ZONEFILE_PATH", TEST_ZONE_FILE_PATH):
        with patch("app.ssh_zone_master.DNS_SERVER_LIST", test_dns_servers):
            result = await getDomainZoneMaster(test_domain, debug_flag=True)

            expected_result = {
                "domain": test_domain,
                "answers": [
                    {"ns": host, "zone_master": ""} for host in test_dns_servers
                ],
            }
            assert result == expected_result
