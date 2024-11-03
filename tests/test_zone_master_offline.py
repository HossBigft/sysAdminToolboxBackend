from app.ssh_zone_master import (
    is_valid_domain,
    build_zone_master_command,
    getDomainZoneMaster,
)
from .test_data.hosts import HostList
import pytest
from unittest.mock import patch, AsyncMock
import shlex


def test_valid_domain(domain=HostList.CORRECT_EXISTING_SUBDOMAIN):
    assert is_valid_domain(domain)


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


@pytest.mark.parametrize("domain", invalid_domains)
def test_invalid_domain(domain):
    assert not is_valid_domain(domain)


@pytest.mark.asyncio
async def test_get_domain_zone_master_with_correct_domain_existing_zone_master(
    domain=HostList.CORRECT_EXISTING_DOMAIN,
):
    mock_response = [
example.com
example.com
example.com
    ]

    with patch(
        "app.ssh_zone_master.batch_ssh_command_prepare", new_callable=AsyncMock
    ) as mock_batch_ssh:
        mock_batch_ssh.return_value = mock_response

        result = await getDomainZoneMaster(domain)

        expected_result = {
            "domain": domain,
            "answers": [
example.com
example.com
example.com
            ],
        }
        assert result == expected_result
        mock_batch_ssh.assert_called_once()


@pytest.mark.asyncio
async def test_get_domain_zone_master_with_correct_domain_nonexisting_zone_master(
    domain=HostList.DOMAIN_WITHOUT_ZONE_MASTER,
):
    mock_response = [
example.com
example.com
example.com
    ]

    with patch(
        "app.ssh_zone_master.batch_ssh_command_prepare", new_callable=AsyncMock
    ) as mock_batch_ssh:
        mock_batch_ssh.return_value = mock_response
        result = await getDomainZoneMaster(domain)

        assert result is None
        mock_batch_ssh.assert_called_once()


def test_command_injection_sanitization(
    domain=HostList.CORRECT_EXISTING_DOMAIN + ";echo hello",
):
    expected_grep_pattern = shlex.quote(f'\\"{domain.lower()}\\"')
    expected = (
        r"cat /var/opt/isc/scls/isc-bind/zones/_default.nzf | "
        f"grep {expected_grep_pattern} | "
        r"grep -Po '((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}' | "
        "head -n1"
    )
    assert build_zone_master_command(domain) == expected
