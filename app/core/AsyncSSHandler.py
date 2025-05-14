import asyncio
import time
from typing import List

from app.schemas import SSHCommandResult
from app.core.config import settings


async def _execute_ssh_command(host, command) -> SSHCommandResult:
    verbose: bool = settings.ENVIRONMENT == "local"
    start_time = time.time()

    ssh_command = f'ssh -q  {host} "{command}"'
    process = await asyncio.create_subprocess_shell(
        ssh_command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    if verbose:
        print(f"{host} {ssh_command}| Awaiting result...")

    stdout, stderr = await process.communicate()

    end_time = time.time()
    execution_time = end_time - start_time

    if verbose:
        succesfulAnswer = stdout.decode().strip().rstrip()
        failAnswer = stderr.decode().strip().rstrip()
        if failAnswer:
            print(f"{host} failed in {execution_time:.2f}s : {failAnswer}")
        else:
            print(f"{host} answered in {execution_time:.2f}s : {succesfulAnswer}")

    stdout_output: str | None = (
        stdout.decode().strip() if stdout.decode().strip() != "" else None
    )
    stderr_output: str | None = (
        stderr.decode().strip() if stderr.decode().strip() != "" else None
    )
    returncode_output: int | None = process.returncode
    return {
        "host": host,
        "stdout": stdout_output,
        "stderr": stderr_output,
        "returncode": returncode_output,
    }


async def execute_ssh_commands_in_batch(server_list, command) -> List[SSHCommandResult]:
    tasks = [_execute_ssh_command(host, command) for host in server_list]
    results = await asyncio.gather(*tasks)
    return results


async def execute_ssh_command(host: str, command: str) -> SSHCommandResult:
    result = await asyncio.gather(_execute_ssh_command(host, command))
    return result[0]
