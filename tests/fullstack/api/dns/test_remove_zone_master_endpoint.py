import pytest
from httpx import AsyncClient

from tests.test_data.hosts import HostList


@pytest.mark.asyncio
async def test_remove_zone_master_permissions_error(
    client: AsyncClient, normal_user_token_headers: dict[str, str]
) -> None:
    r = await client.delete(
        f"/dns/internal/zonemaster/?domain={HostList.CORRECT_EXISTING_DOMAIN}",
        headers=normal_user_token_headers,
    )
    assert r.status_code == 403
    assert r.json() == {"detail": "The user doesn't have enough privileges"}


@pytest.mark.asyncio
async def test_remove_zone_master_nonexisting_domain(
    client: AsyncClient, normal_user_token_headers: dict[str, str]
) -> None:
    r = await client.delete(
        f"/dns/internal/zonemaster/?domain={HostList.CORRECT_NONEXISTING_DOMAIN}",
        headers=normal_user_token_headers,
    )
    assert r.status_code == 404
