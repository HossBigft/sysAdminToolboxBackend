from app.ssh_zone_master import (
    is_valid_domain,
    build_zone_master_command,
)
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


def test_basic_domain(domain=HostList.CORRECT_EXISTING_DOMAIN):
    expected = (
        r"cat /var/opt/isc/scls/isc-bind/zones/_default.nzf | "
        f"grep {domain} | "
        r"grep -Po '((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\\b){{4}}' | "
        "head -n1"
    )
    assert build_zone_master_command(domain) == expected


def test_special_characters(domain=HostList.MALFORMED_DOMAIN):
    expected = (
        r"cat /var/opt/isc/scls/isc-bind/zones/_default.nzf | "
        f"grep {domain} | "
        r"grep -Po '((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\\b){{4}}' | "
        "head -n1"
    )
    assert build_zone_master_command(domain) == expected


def test_lowercase_conversion(domain=HostList.CORRECT_EXISTING_DOMAIN.upper()):
    expected = (
        r"cat /var/opt/isc/scls/isc-bind/zones/_default.nzf | "
        f"grep {domain.lower()} | "
        r"grep -Po '((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\\b){{4}}' | "
        "head -n1"
    )
    assert build_zone_master_command(domain) == expected
