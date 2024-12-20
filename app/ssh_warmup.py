from fastapi_utils.tasks import repeat_every

from app.host_lists import DNS_SERVER_LIST
from app.ssh_async_executor import batch_ssh_command_prepare
from app.host_lists import PLESK_SERVER_LIST


@repeat_every(seconds=60 * 5)
async def ssh_warmup() -> None:
    await batch_ssh_command_prepare(
        server_list=PLESK_SERVER_LIST + DNS_SERVER_LIST,
        command="echo online",
        verbose=True,
    )
