import pytest
import shlex
from unittest.mock import patch, AsyncMock

from app.api.dns.ssh_utils import (
    build_get_zone_master_command,
    dns_query_domain_zone_master,
)
from tests.test_data.hosts import HostList
from app.schemas import SubscriptionName

invalid_domains = [
    "ex",  # Too short
    "example..com",  # Double dot
    "-example.com",  # Leading dash
    "example.com-",  # Trailing dash
    "example.com.",  # Trailing dot
    "example@com",  # Invalid character '@'
    "IP_PLACEHOLDER",  # Not a domain
    "invalid_domain",  # Invalid format
    "example.c",  # Top-level domain too short
    "a" * 64 + ".com",  # Too long (64 characters)
    HostList.MALFORMED_DOMAIN,
]


@pytest.mark.asyncio
async def test_dns_get_domain_zone_master_with_correct_domain_existing_zone_master(
    domain=HostList.CORRECT_EXISTING_DOMAIN,
):
    mock_response = [
        {"host": "ns1.internal.kz.", "stdout": "IP_PLACEHOLDER"},
        {"host": "ns2.internal.kz.", "stdout": "IP_PLACEHOLDER"},
        {"host": "ns3.internal.kz.", "stdout": "IP_PLACEHOLDER"},
    ]

    with patch(
        "app.api.dns.ssh_utils.batch_ssh_execute", new_callable=AsyncMock
    ) as mock_batch_ssh:
        mock_batch_ssh.return_value = mock_response

        result = await dns_query_domain_zone_master(SubscriptionName(name=domain))

        expected_result = {
            "domain": domain,
            "answers": [
                {"ns": "ns1.internal.kz.", "zone_master": "IP_PLACEHOLDER"},
                {"ns": "ns2.internal.kz.", "zone_master": "IP_PLACEHOLDER"},
                {"ns": "ns3.internal.kz.", "zone_master": "IP_PLACEHOLDER"},
            ],
        }
        assert result == expected_result
        mock_batch_ssh.assert_called_once()


@pytest.mark.asyncio
async def test_dns_get_domain_zone_master_with_correct_domain_nonexisting_zone_master(
    domain=HostList.DOMAIN_WITHOUT_ZONE_MASTER,
):
    mock_response = [
        {"host": "ns1.internal.kz.", "stdout": ""},
        {"host": "ns2.internal.kz.", "stdout": ""},
        {"host": "ns3.internal.kz.", "stdout": ""},
    ]

    with patch(
        "app.api.dns.ssh_utils.batch_ssh_execute", new_callable=AsyncMock
    ) as mock_batch_ssh:
        mock_batch_ssh.return_value = mock_response
        result = await dns_query_domain_zone_master(SubscriptionName(name=domain))

        assert result is None
        mock_batch_ssh.assert_called_once()
