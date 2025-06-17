import asyncio
import time
import traceback
from scalene import scalene_profiler

from app.signed_executor.async_ssh_handler import (
    execute_ssh_commands_in_batch,
    initialize_connection_pool,
)
from app.schemas import PLESK_SERVER_LIST, DNS_SERVER_LIST

SLEEP_TIME = 5


async def main():
    loop = asyncio.get_running_loop()

    original_run_in_executor = loop.run_in_executor

    def debug_run_in_executor(executor, func, *args):
        print("[run_in_executor called]")
        traceback.print_stack()
        return original_run_in_executor(executor, func, *args)

    loop.run_in_executor = debug_run_in_executor

    print("Initialising connection pool")
    await initialize_connection_pool(PLESK_SERVER_LIST + DNS_SERVER_LIST)

    print(f"Sleeping {SLEEP_TIME}s. to cool the CPU")
    time.sleep(SLEEP_TIME)
    
    print("Running requests on cold connections")
    await execute_ssh_commands_in_batch(
        PLESK_SERVER_LIST + DNS_SERVER_LIST, command="status"
    )

    scalene_profiler.start()
    print("Running requests on warmed connections")
    await execute_ssh_commands_in_batch(
        PLESK_SERVER_LIST + DNS_SERVER_LIST, command="status"
    )
    scalene_profiler.stop()


if __name__ == "__main__":
    asyncio.run(main())
