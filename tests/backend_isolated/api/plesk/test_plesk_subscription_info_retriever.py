import pytest
from app.plesk.ssh_utils import (
    is_valid_subscription_name,
    build_subscription_info_query,
    extract_subscription_details,
)
from tests.test_data.hosts import HostList


def test_valid_domain(domain=HostList.CORRECT_EXISTING_SUBDOMAIN):
    assert is_valid_subscription_name(domain)


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
    assert not is_valid_subscription_name(domain)


def test_query_builder(domain=HostList.CORRECT_EXISTING_DOMAIN):
    correct_query = (
        "SELECT CASE WHEN webspace_id = 0 THEN id ELSE webspace_id END AS result "
        "FROM domains WHERE name LIKE '{0}'; "
        "SELECT name FROM domains WHERE id=(SELECT CASE WHEN webspace_id = 0 THEN id ELSE webspace_id END AS result FROM domains WHERE name LIKE '{0}'); "
        "SELECT pname, login FROM clients WHERE id=(SELECT cl_id FROM domains WHERE name LIKE '{0}'); "
        "SELECT name FROM domains WHERE webspace_id=(SELECT CASE WHEN webspace_id = 0 THEN id ELSE webspace_id END AS result FROM domains WHERE name LIKE '{0}');"
    ).format(domain)

    assert build_subscription_info_query(domain) == correct_query


def test_extract_subscription_details():
    sample_input = {
        "host": "example.com",
        "stdout": "12345\nTest Name\nuser1\tlogin1\ndomain1.com\ndomain2.com",
    }

    expected_output = {
        "host": "example.com",
        "id": "12345",
        "name": "Test Name",
        "username": "user1",
        "userlogin": "login1",
        "domains": ["Test Name", "domain1.com", "domain2.com"],
    }

    result = extract_subscription_details(sample_input)

    assert result == expected_output


def test_extract_subscription_details_empty_stdout():
    sample_input = {"host": "example.com", "stdout": "\n\n\n\n"}

    result = extract_subscription_details(sample_input)
    assert result is None


def test_parse_correct_answer():
    sample_input = {
        "host": "pleskserver.",
google.com
    }

    expected_output = {
        "host": "pleskserver.",
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

    result = extract_subscription_details(sample_input)

    assert result == expected_output
