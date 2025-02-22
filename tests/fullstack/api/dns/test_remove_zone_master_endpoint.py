import pytest
from httpx import AsyncClient

from unittest.mock import AsyncMock, patch
from tests.test_data.hosts import HostList


@pytest.mark.asyncio
async def test_remove_zone_master_permissions_error(
    client: AsyncClient, normal_user_token_headers: dict[str, str]
) -> None:
    with (
        patch(
            "app.api.dns.dns_router.dns_get_domain_zone_master", new_callable=AsyncMock
        ) as mock_get_zone,
        patch(
            "app.api.dns.dns_router.dns_remove_domain_zone_master", new_callable=AsyncMock
        ) as mock_remove,
    ):
        mock_remove.side_effect = RuntimeError("Zone not found")
        mock_get_zone.return_value = None
        r = await client.delete(
            f"/dns/internal/zonemaster/?domain={HostList.CORRECT_EXISTING_DOMAIN}",
            headers=normal_user_token_headers,
        )
        assert r.status_code == 403
        assert r.json() == {"detail": "The user doesn't have enough privileges"}


@pytest.mark.asyncio
async def test_remove_zone_master_nonexisting_domain(
    client: AsyncClient, superuser_token_headers: dict[str, str]
) -> None:
    with (
        patch(
            "app.api.dns.dns_router.dns_get_domain_zone_master", new_callable=AsyncMock
        ) as mock_get_zone,
        patch(
            "app.api.dns.dns_router.dns_remove_domain_zone_master", new_callable=AsyncMock
        ) as mock_remove,
    ):
        mock_remove.side_effect = RuntimeError("Zone not found")
        mock_get_zone.return_value = None
        r = await client.delete(
            f"/dns/internal/zonemaster/?domain={HostList.CORRECT_NONEXISTING_DOMAIN}",
            headers=superuser_token_headers,
        )
    assert r.status_code == 404
