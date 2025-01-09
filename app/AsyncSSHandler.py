import asyncio
from typing import List, TypedDict
import time


class SSHCommandResult(TypedDict):
    host: str
    stdout: str | None
    stderr: str | None
    returncode: int | None


async def _execute_ssh_command(host, command, verbose: bool) -> SSHCommandResult:
    start_time = time.time()

    ssh_command = f'ssh -q  {host} "{command}"'
    process = await asyncio.create_subprocess_shell(
        ssh_command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    if verbose:
        print(f"{host} {ssh_command}| Awaiting result...")

    stdout, stderr = await process.communicate()

    # Record the end time after the command finishes
    end_time = time.time()

    # Calculate the elapsed time
    execution_time = end_time - start_time

    if verbose:
        succesfulAnswer = stdout.decode().strip().rstrip()
        failAnswer = stderr.decode().strip().rstrip()
        if failAnswer:
            print(f"{host} failed in {execution_time:.2f}s : {failAnswer}")
        else:
            print(f"{host} answered in {execution_time:.2f}s : {succesfulAnswer}")

    stdout_output = stdout.decode().strip() if stdout.decode().strip() != "" else None
    stderr_output = stderr.decode().strip() if stderr.decode().strip() != "" else None
    returncode_output = process.returncode if process.returncode else None
    return {
        "host": host,
        "stdout": stdout_output,
        "stderr": stderr_output,
        "returncode": returncode_output,
    }


async def execute_ssh_commands_in_batch(
    server_list, command, verbose: bool
) -> List[SSHCommandResult]:
    tasks = [_execute_ssh_command(host, command, verbose) for host in server_list]
    results = await asyncio.gather(*tasks)
    return results


async def execute_ssh_command(
    host: str, command: str, verbose: bool = True
) -> SSHCommandResult:
    result = await asyncio.gather(_execute_ssh_command(host, command, verbose))
    return result[0]
