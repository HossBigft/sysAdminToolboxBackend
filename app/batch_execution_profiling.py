import time
from scalene import scalene_profiler
import uvloop

from app.signed_executor.async_ssh_handler import (
    execute_ssh_commands_in_batch,
    initialize_connection_pool,
)
from app.schemas import PLESK_SERVER_LIST, DNS_SERVER_LIST

SLEEP_TIME = 5


async def main():
    print("Initialising connection pool")
    server_list = PLESK_SERVER_LIST + DNS_SERVER_LIST
    server_list = server_list

    await initialize_connection_pool(server_list)

    print(f"Sleeping {SLEEP_TIME}s. to cool the CPU")
    time.sleep(SLEEP_TIME)

    print("Running requests on cold connections")
    await execute_ssh_commands_in_batch(server_list, command="status")

    scalene_profiler.start()
    print("Running requests on warmed connections")
    await execute_ssh_commands_in_batch(server_list, command="status")
    scalene_profiler.stop()


if __name__ == "__main__":
    uvloop.run(main())
