from fastapi_utils.tasks import repeat_every
from app.core.AsyncSSHandler import execute_ssh_commands_in_batch
from app.schemas import PLESK_SERVER_LIST, DNS_SERVER_LIST


@repeat_every(seconds=60 * 5)
async def ssh_warmup() -> None:
    await execute_ssh_commands_in_batch(
        server_list=PLESK_SERVER_LIST + DNS_SERVER_LIST,
        command="status",

    )
