import re

from app.host_lists import PLESK_SERVER_LIST
from app.ssh_async_executor import run_command_over_ssh

PLESK_LOGLINK_CMD = "plesk login"
LINUX_USERNAME_PATTERN = r"^[a-z_]([a-z0-9_-]{0,31}|[a-z0-9_-]{0,30}\$)$"
REDIRECTION_HEADER = r"&success_redirect_url=%2Fadmin%2Fsubscription%2Foverview%2Fid%2F"


async def _is_valid_username(username: str) -> bool:
    return bool(re.match(LINUX_USERNAME_PATTERN, username))


async def _build_login_command(username: str) -> str:
    return f"plesk login {username}"


async def _is_subscription_id_valid(host: str, subscriptionId: str) -> bool:
    get_subscription_name_cmd = f'plesk db -Ne "SELECT name FROM domains WHERE webspace_id=0 AND id={subscriptionId}"'
    subscription_name = await run_command_over_ssh(
        host, get_subscription_name_cmd
    ).stdout

    return not subscription_name == ""


async def get_plesk_login_link(host: str, username: str) -> str:
    if host not in PLESK_SERVER_LIST:
        raise ValueError(f"Host '{host}' is not Plesk server.")
    if not _is_valid_username(username):
        raise ValueError("Input string should be a valid linux username.")
    cmd_to_run = await _build_login_command(username)
    answer = await run_command_over_ssh(cmd_to_run)
    return answer.stdout


async def get_plesk_subscription_login_link_by_id(
    host: str, subscription_id: int, username: str
) -> str:
    if host not in PLESK_SERVER_LIST:
        raise ValueError(f"Host '{host}' is not a Plesk server.")

    if not _is_valid_username(username):
        raise ValueError("Input string should be a valid Linux username.")

    if not await _is_subscription_id_valid(host, subscription_id):
        raise ValueError("Subscription with the provided ID doesn't exist.")

    plesk_login_link = await get_plesk_login_link(host, username)
    subscription_login_link = f"{plesk_login_link}{REDIRECTION_HEADER}{subscription_id}"

    return subscription_login_link
