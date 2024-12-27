import pytest
import shlex
from unittest.mock import patch, AsyncMock

from app.dns.ssh_utils import (
    is_valid_domain,
    build_get_zone_master_command,
    get_domain_zone_master_data,
)
from tests.test_data.hosts import HostList



@pytest.mark.asyncio
async def test_valid_domain(domain=HostList.CORRECT_EXISTING_SUBDOMAIN):
    assert await is_valid_domain(domain)


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
@pytest.mark.parametrize("domain", invalid_domains)
async def test_invalid_domain(domain):
    assert not await is_valid_domain(domain)


@pytest.mark.asyncio
async def test_get_domain_zone_master_with_correct_domain_existing_zone_master(
    domain=HostList.CORRECT_EXISTING_DOMAIN,
):
    mock_response = [
        {"host": "ns1.internal.kz.", "stdout": "IP_PLACEHOLDER"},
        {"host": "ns2.internal.kz.", "stdout": "IP_PLACEHOLDER"},
        {"host": "ns3.internal.kz.", "stdout": "IP_PLACEHOLDER"},
    ]

    with patch(
        "app.dns.ssh_utils.batch_ssh_execute", new_callable=AsyncMock
    ) as mock_batch_ssh:
        mock_batch_ssh.return_value = mock_response

        result = await get_domain_zone_master_data(domain)

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
async def test_get_domain_zone_master_with_correct_domain_nonexisting_zone_master(
    domain=HostList.DOMAIN_WITHOUT_ZONE_MASTER,
):
    mock_response = [
        {"host": "ns1.internal.kz.", "stdout": ""},
        {"host": "ns2.internal.kz.", "stdout": ""},
        {"host": "ns3.internal.kz.", "stdout": ""},
    ]

    with patch(
        "app.dns.ssh_utils.batch_ssh_execute", new_callable=AsyncMock
    ) as mock_batch_ssh:
        mock_batch_ssh.return_value = mock_response
        result = await get_domain_zone_master_data(domain)

        assert result is None
        mock_batch_ssh.assert_called_once()


@pytest.mark.asyncio
async def test_command_injection_sanitization(
    domain=HostList.CORRECT_EXISTING_DOMAIN + ";echo hello",
):
    expected_grep_pattern = shlex.quote(f'\\"{domain.lower()}\\"')
    expected = (
        r"cat /var/opt/isc/scls/isc-bind/zones/_default.nzf | "
        f"grep {expected_grep_pattern} | "
        r"grep -Po '((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}' | "
        "head -n1"
    )
    assert await build_get_zone_master_command(domain) == expected
