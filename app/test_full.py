from fastapi.testclient import TestClient
from .main import app
from .data_command_injection_list import COMMAND_INJECTION_LIST
from .sql_injection_lists import (
    AUTH_BYPASS_SQL_QUERY_LIST,
    GENERIC_INJECTION_SQL_QUERY_LIST,
    GENERIC_ERRORBASED_SQL_QUERY_LIST,
    GENERIC_TIMEBASED_INJECTION_SQL_QUERY_LIST,
)

import pytest

example.com
google.com
google.com
MALFORMED_DOMAIN = "googlecom."
IP_WITHOUT_PTR = "IP_PLACEHOLDER"
IP_WITH_PTR = "IP_PLACEHOLDER"


client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_a_record_resolution_with_correct_domain_name():
    response = client.get(f"/resolve/a/?domain={DOMAIN_WITH_EXISTING_A_RECORD}")
    assert response.status_code == 200
    assert response.json() == {
        "domain": DOMAIN_WITH_EXISTING_A_RECORD,
        "value": ["IP_PLACEHOLDER"],
    }


def test_a_record_resolution_with_malformed_domain_name():
    response = client.get(f"/resolve/a/?domain={MALFORMED_DOMAIN}")
    assert response.status_code == 422


def test_ssh_connection():
    correct_response_from_ssh = {
        "host": "vgruzo",
        "stdout": "Hello",
    }
    response = client.get("/plesk/greet")
    assert response.status_code == 200
    assert correct_response_from_ssh in response.json()


@pytest.mark.parametrize("command", COMMAND_INJECTION_LIST)
def test_invalid_commands_trigger_422_error(command):
    response = client.get(f"/resolve/zonemaster/?domain={command}")
    assert response.status_code == 422


def test_mx_record_resolution_with_correct_domain_name():
    response = client.get(f"/resolve/mx/?domain={DOMAIN_WITH_EXISTING_MX_RECORD}")
    assert response.status_code == 200
    assert response.json() == {
        "domain": DOMAIN_WITH_EXISTING_MX_RECORD,
google.com
    }


def test_mx_record_resolution_with_malformed_domain_name():
    response = client.get(f"/resolve/mx/?domain={MALFORMED_DOMAIN}")
    assert response.status_code == 422


def test_mx_record_resolution_with_nonexistant_domain_name():
    response = client.get(f"/resolve/mx/?domain={DOMAIN_WITHOUT_RECORDS}")
    assert response.status_code == 404


def test_a_record_resolution_with_nonexistant_domain_name():
    response = client.get(f"/resolve/a/?domain={DOMAIN_WITHOUT_RECORDS}")
    assert response.status_code == 404


def test_ptr_record_resolution_with_nonexistant_ptr_record():
    response = client.get(f"/resolve/ptr/?ip={IP_WITHOUT_PTR}")
    assert response.status_code == 404


def test_ptr_record_resolution():
    response = client.get(f"/resolve/ptr/?ip={IP_WITH_PTR}")
    assert response.json() == {
        "ip": IP_WITH_PTR,
example.com
    }


@pytest.mark.parametrize("injection_query", AUTH_BYPASS_SQL_QUERY_LIST)
def test_subscription_query_against_authentification_bypass_sql_injection(
    injection_query,
):
    response = client.get(f"/plesk/get/subscription/?domain={injection_query}")
    assert response.status_code == 422


@pytest.mark.parametrize("injection_query", GENERIC_INJECTION_SQL_QUERY_LIST)
def test_subscription_query_against_generic_sql_injection(injection_query):
    response = client.get(f"/plesk/get/subscription/?domain={injection_query}")
    assert response.status_code == 422


@pytest.mark.parametrize("injection_query", GENERIC_ERRORBASED_SQL_QUERY_LIST)
def test_subscription_query_against_generic_errorbased_sql_injection(injection_query):
    response = client.get(f"/plesk/get/subscription/?domain={injection_query}")
    assert response.status_code == 422


@pytest.mark.parametrize("injection_query", GENERIC_TIMEBASED_INJECTION_SQL_QUERY_LIST)
def test_subscription_query_against_generic_timebased_sql_injection(injection_query):
    response = client.get(f"/plesk/get/subscription/?domain={injection_query}")
    assert response.status_code == 422
