from app.host_lists import DNS_SERVER_LIST
from app.ssh_async_executor import batch_ssh_command_prepare
from app.host_lists import PLESK_SERVER_LIST


async def ssh_warmup() -> None:
    await batch_ssh_command_prepare(
        server_list=PLESK_SERVER_LIST + DNS_SERVER_LIST,
        command="echo online",
        verbose=True,
    )
