from httpx import AsyncClient
import pytest

from tests.test_data.data_command_injection_list import COMMAND_INJECTION_LIST
from tests.test_data.sql_injection_lists import (
    AUTH_BYPASS_SQL_QUERY_LIST,
    GENERIC_INJECTION_SQL_QUERY_LIST,
    GENERIC_ERRORBASED_SQL_QUERY_LIST,
    GENERIC_TIMEBASED_INJECTION_SQL_QUERY_LIST,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("command", COMMAND_INJECTION_LIST)
async def test_command_injection_returns_422_error_get_zonemaster(
    client: AsyncClient, superuser_token_headers: dict[str, str], command
):
    response = await client.get(
        f"/dns/internal/zonemaster/?domain={command}", headers=superuser_token_headers
    )
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("injection_query", AUTH_BYPASS_SQL_QUERY_LIST)
async def test_subscription_query_against_authentification_bypass_sql_injection(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
    injection_query,
):
    response = await client.get(
        f"/plesk/get/subscription/?domain={injection_query}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("injection_query", GENERIC_INJECTION_SQL_QUERY_LIST)
async def test_subscription_query_against_generic_sql_injection(
    client: AsyncClient, superuser_token_headers: dict[str, str], injection_query
):
    response = await client.get(
        f"/plesk/get/subscription/?domain={injection_query}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("injection_query", GENERIC_ERRORBASED_SQL_QUERY_LIST)
async def test_subscription_query_against_generic_errorbased_sql_injection(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
    injection_query,
):
    response = await client.get(
        f"/plesk/get/subscription/?domain={injection_query}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("injection_query", GENERIC_TIMEBASED_INJECTION_SQL_QUERY_LIST)
async def test_subscription_query_against_generic_timebased_sql_injection(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
    injection_query,
):
    response = await client.get(
        f"/plesk/get/subscription/?domain={injection_query}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 422
