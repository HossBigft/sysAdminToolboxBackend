from app.ssh_zone_master import is_valid_domain
from .test_data.hosts import HostList
import pytest


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
