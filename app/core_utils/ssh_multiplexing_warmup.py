from fastapi_utils.tasks import repeat_every
from app.signed_executor.signed_executor_client import get_executor_status_from_servers
from app.schemas import PLESK_SERVER_LIST, DNS_SERVER_LIST


@repeat_every(seconds=60 * 5)
async def ssh_multiplexing_warmup() -> None:
    await get_executor_status_from_servers(server_list=PLESK_SERVER_LIST + DNS_SERVER_LIST)