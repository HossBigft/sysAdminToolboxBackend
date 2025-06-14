import asyncio

from app.signed_executor.async_ssh_handler import execute_ssh_commands_in_batch
from app.schemas import PLESK_SERVER_LIST, DNS_SERVER_LIST


async def main():
    print("Running requests on cold connections")
    await execute_ssh_commands_in_batch(PLESK_SERVER_LIST + DNS_SERVER_LIST, command="status")

    print("Running requests on warmed connections")
    await execute_ssh_commands_in_batch(PLESK_SERVER_LIST + DNS_SERVER_LIST, command="status")


if __name__ == "__main__":
    asyncio.run(main())