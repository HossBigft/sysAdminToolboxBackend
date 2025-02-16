import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch, MagicMock


from app.dns.router import delete_zone_file_for_domain
from app.schemas import SubscriptionName, Message, DomainName
from app.dns.ssh_utils import (
    build_remove_zone_master_command,
    dns_remove_domain_zone_master,
)

TEST_DOMAIN = "example.com"
TEST_EMAIL = "test@example.com"


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_background_tasks():
    return MagicMock()


@pytest.fixture
def mock_current_user():
    return MagicMock(id=1, email=TEST_EMAIL)


@pytest.mark.asyncio
async def test_delete_zone_file_success(
    mock_session, mock_background_tasks, mock_current_user
):
    domain = SubscriptionName(domain=TEST_DOMAIN)
    current_zone = "zonemaster.com"
    with (
        patch(
            "app.dns.router.dns_get_domain_zone_master", new_callable=AsyncMock
        ) as mock_get_zone,
        patch(
            "app.dns.router.dns_remove_domain_zone_master", new_callable=AsyncMock
        ) as mock_remove,
        patch(
            "app.dns.router.add_dns_remove_zone_master_log_entry",
            new_callable=AsyncMock,
        ) as mock_history,
    ):
        mock_get_zone.return_value = current_zone
        response = await delete_zone_file_for_domain(
            session=mock_session,
            background_tasks=mock_background_tasks,
            current_user=mock_current_user,
            domain=domain,
        )

        assert isinstance(response, Message)
        assert response.message == "Zone master deleted successfully"

        mock_get_zone.assert_called_once_with(domain)
        mock_remove.assert_called_once_with(domain)
        mock_background_tasks.add_task.assert_called_once_with(
            mock_history,
            session=mock_session,
            db_user=mock_current_user,
            current_zone_master=DomainName(domain="zonemaster.com"),
        )


@pytest.mark.asyncio
async def test_delete_zone_file_not_found(
    mock_session, mock_background_tasks, mock_current_user
):
    domain = SubscriptionName(domain="nonexistent.com")

    with (
        patch(
            "app.dns.router.dns_get_domain_zone_master", new_callable=AsyncMock
        ) as mock_get_zone,
        patch(
            "app.dns.router.dns_remove_domain_zone_master", new_callable=AsyncMock
        ) as mock_remove,
    ):
        mock_get_zone.return_value = None
        mock_remove.side_effect = RuntimeError("Zone not found")

        with pytest.raises(HTTPException) as exc_info:
            await delete_zone_file_for_domain(
                session=mock_session,
                background_tasks=mock_background_tasks,
                current_user=mock_current_user,
                domain=domain,
            )

        assert exc_info.value.status_code == 404
        assert str(exc_info.value.detail) == "Zone not found"


@pytest.mark.asyncio
async def test_build_remove_zone_master_command():
    domain = SubscriptionName(domain="test.com")
    command = await build_remove_zone_master_command(domain)
    expected = "/opt/isc/isc-bind/root/usr/sbin/rndc delzone -clean test.com"
    assert command == expected


@pytest.mark.asyncio
async def test_dns_remove_domain_zone_master_success():
    domain = SubscriptionName(domain="test.com")
    mock_response = [{"host": "dns1", "stderr": ""}]

    with patch(
        "app.dns.ssh_utils.batch_ssh_execute", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = mock_response
        await dns_remove_domain_zone_master(domain)
        mock_execute.assert_called_once()


@pytest.mark.asyncio
async def test_dns_remove_domain_zone_master_error():
    domain = SubscriptionName(domain="test.com")
    mock_response = [{"host": "dns1", "stderr": "error occurred"}]

    with patch(
        "app.dns.ssh_utils.batch_ssh_execute", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = mock_response

        with pytest.raises(RuntimeError) as exc_info:
            await dns_remove_domain_zone_master(domain)

        assert "DNS zone removal failed for host: dns1" in str(exc_info.value)
