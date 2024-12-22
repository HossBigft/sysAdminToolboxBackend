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
        "records": ["IP_PLACEHOLDER"],
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
async def test_invalid_commands_trigger_422_error(
    client: AsyncClient, superuser_token_headers: dict[str, str], command
):
    response = await client.get(
        f"/dns/internal/get/zonemaster/?domain={command}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_mx_record_resolution_with_correct_domain_name(
    client: AsyncClient,
    domain=HostList.DOMAIN_WITH_EXISTING_MX_RECORD,
):
    response = await client.get(f"/dns/internal/resolve/mx/?domain={domain}")
    assert response.status_code == 200
    assert response.json() == {
        "domain": domain,
        "records": [f"mail.{domain}."],
    }


@pytest.mark.asyncio
async def test_mx_record_resolution_with_malformed_domain_name(
    client: AsyncClient,
    domain=HostList.MALFORMED_DOMAIN,
):
    response = await client.get(f"/dns/internal/resolve/mx/?domain={domain}")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_mx_record_resolution_with_nonexistant_domain_name(
    client: AsyncClient,
    domain=HostList.DOMAIN_WITHOUT_ZONE_MASTER,
):
    response = await client.get(f"/dns/internal/resolve/mx/?domain={domain}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_a_record_resolution_with_nonexistant_domain_name(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
    domain=HostList.DOMAIN_WITHOUT_ZONE_MASTER,
):
    response = await client.get(
        f"/dns/internal/resolve/a/?domain={domain}", headers=superuser_token_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_ptr_record_resolution_with_nonexistant_ptr_record(
    client: AsyncClient,
    domain=HostList.IP_WITHOUT_PTR,
):
    response = await client.get(f"/dns/resolve/ptr/?ip={domain}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_ptr_record_resolution(client: AsyncClient, domain=HostList.IP_WITH_PTR):
    response = await client.get(f"/dns/resolve/ptr/?ip={domain}")
    assert response.json() == {
        "ip": domain,
example.com
    }


@pytest.mark.asyncio
async def test_subscription_query_with_malformed_domain_name(
    client: AsyncClient,
    domain=HostList.MALFORMED_DOMAIN,
):
    response = await client.get(f"/plesk/get/subscription/?domain={domain}")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ns_record_resolution_with_correct_domain_name(
    client: AsyncClient,
    domain=HostList.CORRECT_EXISTING_DOMAIN,
):
    response = await client.get(f"/dns/resolve/ns/?domain={domain}")
    assert response.status_code == 200
    assert response.json() == {
        "domain": domain,
example.com
    }


@pytest.mark.asyncio
async def test_ns_record_resolution_with_malformed_domain_name(
    client: AsyncClient,
    domain=HostList.MALFORMED_DOMAIN,
):
    response = await client.get(f"/dns/resolve/ns/?domain={domain}")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ns_record_resolution_with_nonexistant_domain_name(
    client: AsyncClient,
    domain=HostList.DOMAIN_WITHOUT_ZONE_MASTER,
):
    response = await client.get(f"/dns/resolve/ns/?domain={domain}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_ns_record_resolution_with_correct_subdomain(
    client: AsyncClient,
    domain=HostList.CORRECT_EXISTING_SUBDOMAIN,
):
    response = await client.get(f"/dns/resolve/ns/?domain={domain}")
    assert response.status_code == 200
    assert response.json() == {
        "domain": domain,
example.com
    }
