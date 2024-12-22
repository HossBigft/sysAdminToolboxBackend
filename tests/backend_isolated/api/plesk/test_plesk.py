from httpx import AsyncClient
import pytest
from tests.test_data.hosts import HostList


@pytest.mark.asyncio
async def test_subscription_query_with_malformed_domain_name(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
    domain=HostList.MALFORMED_DOMAIN,
):
    response = await client.get(
        f"/plesk/get/subscription/?domain={domain}", headers=superuser_token_headers
    )
    assert response.status_code == 422
