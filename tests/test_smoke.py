from fastapi.testclient import TestClient
from app.main import app
from .test_data.data_command_injection_list import COMMAND_INJECTION_LIST
import pytest

example.com
google.com
google.com
google.com
MALFORMED_DOMAIN = "googlecom."
IP_WITHOUT_PTR = "IP_PLACEHOLDER"
IP_WITH_PTR = "IP_PLACEHOLDER"
google.com

client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_a_record_resolution_with_correct_domain_name():
    response = client.get(f"/dns/resolve/a/?domain={DOMAIN_WITH_EXISTING_A_RECORD}")
    assert response.status_code == 200
    assert response.json() == {
        "domain": DOMAIN_WITH_EXISTING_A_RECORD,
        "records": ["IP_PLACEHOLDER"],
    }


def test_a_record_resolution_with_malformed_domain_name():
    response = client.get(f"/dns/resolve/a/?domain={MALFORMED_DOMAIN}")
    assert response.status_code == 422


@pytest.mark.parametrize("command", COMMAND_INJECTION_LIST[:10])
def test_invalid_commands_trigger_422_error(command):
    response = client.get(f"/dns/get/zonemaster/?domain={command}")
    assert response.status_code == 422


def test_mx_record_resolution_with_correct_domain_name(
    domain=DOMAIN_WITH_EXISTING_MX_RECORD,
):
    response = client.get(f"/dns/resolve/mx/?domain={domain}")
    assert response.status_code == 200
    assert response.json() == {
        "domain": domain,
        "records": f"mail.{domain}.",
    }


def test_mx_record_resolution_with_malformed_domain_name():
    response = client.get(f"/dns/resolve/mx/?domain={MALFORMED_DOMAIN}")
    assert response.status_code == 422


def test_mx_record_resolution_with_nonexistant_domain_name():
    response = client.get(f"/dns/resolve/mx/?domain={DOMAIN_WITHOUT_RECORDS}")
    assert response.status_code == 404


def test_a_record_resolution_with_nonexistant_domain_name():
    response = client.get(f"/dns/resolve/a/?domain={DOMAIN_WITHOUT_RECORDS}")
    assert response.status_code == 404


def test_ptr_record_resolution_with_nonexistant_ptr_record():
    response = client.get(f"/dns/resolve/ptr/?ip={IP_WITHOUT_PTR}")
    assert response.status_code == 404


def test_ptr_record_resolution():
    response = client.get(f"/dns/resolve/ptr/?ip={IP_WITH_PTR}")
    assert response.json() == {
        "ip": IP_WITH_PTR,
example.com
    }


def test_subscription_query_with_malformed_domain_name():
    response = client.get(f"/plesk/get/subscription/?domain={MALFORMED_DOMAIN}")
    assert response.status_code == 422


def test_ns_record_resolution_with_correct_domain_name():
    response = client.get(f"/dns/resolve/ns/?domain={CORRECT_EXISTING_DOMAIN}")
    assert response.status_code == 200
    assert response.json() == {
        "domain": CORRECT_EXISTING_DOMAIN,
example.com
    }


def test_ns_record_resolution_with_malformed_domain_name():
    response = client.get(f"/dns/resolve/ns/?domain={MALFORMED_DOMAIN}")
    assert response.status_code == 422


def test_ns_record_resolution_with_nonexistant_domain_name():
    response = client.get(f"/dns/resolve/ns/?domain={DOMAIN_WITHOUT_RECORDS}")
    assert response.status_code == 404


def test_ns_record_resolution_with_correct_subdomain(domain=CORRECT_EXISTING_SUBDOMAIN):
    response = client.get(f"/dns/resolve/ns/?domain={domain}")
    assert response.status_code == 200
    assert response.json() == {
        "domain": domain,
example.com
    }
