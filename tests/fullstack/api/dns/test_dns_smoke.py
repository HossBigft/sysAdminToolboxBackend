from httpx import AsyncClient
import pytest

from tests.test_data.data_command_injection_list import COMMAND_INJECTION_LIST
from tests.test_data.hosts import HostList


@pytest.mark.asyncio
async def test_a_record_resolution_with_correct_domain_name(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
    domain=HostList.DOMAIN_WITH_EXISTING_A_RECORD,
):
    response = await client.get(
        f"/dns/internal/resolve/a/?domain={domain}", headers=superuser_token_headers
    )
    assert response.status_code == 200
    assert response.json() == {
        "domain": domain,
        "records": ["IP_PLACEHOLDER", "IP_PLACEHOLDER"],
    }


@pytest.mark.asyncio
async def test_a_record_resolution_with_malformed_domain_name(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
    domain=HostList.MALFORMED_DOMAIN,
):
    response = await client.get(
        f"/dns/internal/resolve/a/?domain={domain}", headers=superuser_token_headers
    )
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("command", COMMAND_INJECTION_LIST[:10])
async def test_command_injection_returns_422_error_get_zonemaster(
    client: AsyncClient, superuser_token_headers: dict[str, str], command
):
    response = await client.get(
        f"/dns/internal/zonemaster/?domain={command}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_mx_record_resolution_with_correct_domain_name(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
    domain=HostList.DOMAIN_WITH_EXISTING_MX_RECORD,
):
    response = await client.get(
        f"/dns/internal/resolve/mx/?domain={domain}", headers=superuser_token_headers
    )
    assert response.status_code == 200
    assert response.json() == {
        "domain": domain,
        "records": [f"smtp.{domain}."],
    }


@pytest.mark.asyncio
async def test_mx_record_resolution_with_malformed_domain_name(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
    domain=HostList.MALFORMED_DOMAIN,
):
    response = await client.get(
        f"/dns/internal/resolve/mx/?domain={domain}", headers=superuser_token_headers
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_mx_record_resolution_with_nonexistant_domain_name(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
    domain=HostList.CORRECT_NONEXISTING_DOMAIN,
):
    response = await client.get(
        f"/dns/internal/resolve/mx/?domain={domain}", headers=superuser_token_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_a_record_resolution_with_nonexistant_domain_name(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
    domain=HostList.CORRECT_NONEXISTING_DOMAIN,
):
    response = await client.get(
        f"/dns/internal/resolve/a/?domain={domain}", headers=superuser_token_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_ptr_record_resolution_with_nonexistant_ptr_record(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
    domain=HostList.IP_WITHOUT_PTR,
):
    response = await client.get(
        f"/dns/resolve/ptr/?ip={domain}", headers=superuser_token_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_ptr_record_resolution(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
    domain=HostList.IP_WITH_PTR,
):
    response = await client.get(
        f"/dns/resolve/ptr/?ip={domain}", headers=superuser_token_headers
    )
    assert response.json() == {
        "ip": domain,
        "records": ["dns.google."],
    }


@pytest.mark.asyncio
async def test_ns_record_resolution_with_correct_domain_name(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
    domain=HostList.CORRECT_EXISTING_DOMAIN,
):
    response = await client.get(
        f"/dns/resolve/ns/?domain={domain}", headers=superuser_token_headers
    )
    assert response.status_code == 200
    assert response.json() == {
        "domain": domain,
        "records": [
            "ns2.google.com.",
            "ns3.google.com.",
            "ns4.google.com.",
            "ns1.google.com.",
        ],
    }


@pytest.mark.asyncio
async def test_ns_record_resolution_with_malformed_domain_name(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
    domain=HostList.MALFORMED_DOMAIN,
):
    response = await client.get(
        f"/dns/resolve/ns/?domain={domain}", headers=superuser_token_headers
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ns_record_resolution_with_nonexistant_domain_name(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
    domain=HostList.CORRECT_NONEXISTING_DOMAIN,
):
    response = await client.get(
        f"/dns/resolve/ns/?domain={domain}", headers=superuser_token_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_ns_record_resolution_with_correct_subdomain(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
    domain=HostList.CORRECT_EXISTING_SUBDOMAIN,
):
    response = await client.get(
        f"/dns/resolve/ns/?domain={domain}", headers=superuser_token_headers
    )
    assert response.status_code == 200
    assert response.json() == {
        "domain": domain,
        "records": [
            "ns2.google.com.",
            "ns3.google.com.",
            "ns4.google.com.",
            "ns1.google.com.",
        ],
    }


@pytest.mark.asyncio
async def test_ns_record_resolution_without_login(
    client: AsyncClient,
    domain=HostList.CORRECT_EXISTING_DOMAIN,
):
    response = await client.get(f"/dns/resolve/ns/?domain={domain}")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_a_record_resolution_without_login(
    client: AsyncClient,
    domain=HostList.CORRECT_EXISTING_DOMAIN,
):
    response = await client.get(f"/dns/internal/resolve/a/?domain={domain}")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_mx_record_resolution_without_login(
    client: AsyncClient,
    domain=HostList.CORRECT_EXISTING_DOMAIN,
):
    response = await client.get(f"/dns/internal/resolve/mx/?domain={domain}")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_ptr_record_resolution_without_login(
    client: AsyncClient,
    ip=HostList.IP_WITH_PTR,
):
    response = await client.get(f"/dns/resolve/ptr/?domain={ip}")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_delete_zonemaster_without_login(
    client: AsyncClient,
    domain=HostList.CORRECT_EXISTING_DOMAIN,
):
    response = await client.delete(f"/dns/internal/zonemaster/?domain={domain}")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
@pytest.mark.parametrize("command", COMMAND_INJECTION_LIST[:10])
async def test_command_injection_returns_422_error_delete_zonemaster(
    client: AsyncClient, superuser_token_headers: dict[str, str], command
):
    response = await client.get(
        f"/dns/internal/zonemaster/?domain={command}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 422
