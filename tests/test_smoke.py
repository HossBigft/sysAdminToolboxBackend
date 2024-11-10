from fastapi.testclient import TestClient
from app.main import app
from .test_data.data_command_injection_list import COMMAND_INJECTION_LIST
import pytest
from .test_data.hosts import HostList
from app.core.config import settings

client = TestClient(app)
client.base_url = str(client.base_url) + settings.API_V1_STR  # adding prefix
client.base_url = (
    str(client.base_url).rstrip("/") + "/"
)  # making sure we have 1 and only 1 `/`


def test_a_record_resolution_with_correct_domain_name(
    domain=HostList.DOMAIN_WITH_EXISTING_A_RECORD,
):
    response = client.get(f"/dns/hoster/resolve/a/?domain={domain}")
    assert response.status_code == 200
    assert response.json() == {
        "domain": domain,
        "records": ["IP_PLACEHOLDER"],
    }


def test_a_record_resolution_with_malformed_domain_name(
    domain=HostList.MALFORMED_DOMAIN,
):
    response = client.get(f"/dns/hoster/resolve/a/?domain={domain}")
    assert response.status_code == 422


@pytest.mark.parametrize("command", COMMAND_INJECTION_LIST[:10])
def test_invalid_commands_trigger_422_error(command):
    response = client.get(f"/dns/hoster/get/zonemaster/?domain={command}")
    assert response.status_code == 422


def test_mx_record_resolution_with_correct_domain_name(
    domain=HostList.DOMAIN_WITH_EXISTING_MX_RECORD,
):
    response = client.get(f"/dns/hoster/resolve/mx/?domain={domain}")
    assert response.status_code == 200
    assert response.json() == {
        "domain": domain,
        "records": [f"mail.{domain}."],
    }


def test_mx_record_resolution_with_malformed_domain_name(
    domain=HostList.MALFORMED_DOMAIN,
):
    response = client.get(f"/dns/hoster/resolve/mx/?domain={domain}")
    assert response.status_code == 422


def test_mx_record_resolution_with_nonexistant_domain_name(
    domain=HostList.DOMAIN_WITHOUT_ZONE_MASTER,
):
    response = client.get(f"/dns/hoster/resolve/mx/?domain={domain}")
    assert response.status_code == 404


def test_a_record_resolution_with_nonexistant_domain_name(
    domain=HostList.DOMAIN_WITHOUT_ZONE_MASTER,
):
    response = client.get(f"/dns/hoster/resolve/a/?domain={domain}")
    assert response.status_code == 404


def test_ptr_record_resolution_with_nonexistant_ptr_record(
    domain=HostList.IP_WITHOUT_PTR,
):
    response = client.get(f"/dns/resolve/ptr/?ip={domain}")
    assert response.status_code == 404


def test_ptr_record_resolution(domain=HostList.IP_WITH_PTR):
    response = client.get(f"/dns/resolve/ptr/?ip={domain}")
    assert response.json() == {
        "ip": domain,
example.com
    }


def test_subscription_query_with_malformed_domain_name(
    domain=HostList.MALFORMED_DOMAIN,
):
    response = client.get(f"/plesk/get/subscription/?domain={domain}")
    assert response.status_code == 422


def test_ns_record_resolution_with_correct_domain_name(
    domain=HostList.CORRECT_EXISTING_DOMAIN,
):
    response = client.get(f"/dns/resolve/ns/?domain={domain}")
    assert response.status_code == 200
    assert response.json() == {
        "domain": domain,
example.com
    }


def test_ns_record_resolution_with_malformed_domain_name(
    domain=HostList.MALFORMED_DOMAIN,
):
    response = client.get(f"/dns/resolve/ns/?domain={domain}")
    assert response.status_code == 422


def test_ns_record_resolution_with_nonexistant_domain_name(
    domain=HostList.DOMAIN_WITHOUT_ZONE_MASTER,
):
    response = client.get(f"/dns/resolve/ns/?domain={domain}")
    assert response.status_code == 404


def test_ns_record_resolution_with_correct_subdomain(
    domain=HostList.CORRECT_EXISTING_SUBDOMAIN,
):
    response = client.get(f"/dns/resolve/ns/?domain={domain}")
    assert response.status_code == 200
    assert response.json() == {
        "domain": domain,
example.com
    }
