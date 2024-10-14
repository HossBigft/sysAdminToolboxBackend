from app.async_ssh_executor import batch_ssh_command_prepare
from app.host_lists import TEST_SERVER_LIST
from typing import List


async def send_hello() -> List[str]:
    result = await batch_ssh_command_prepare(
        server_list=TEST_SERVER_LIST, command="echo Hello", verbose=False
    )
    return [{"host": item["host"], "stdout": item["stdout"]} for item in result]
