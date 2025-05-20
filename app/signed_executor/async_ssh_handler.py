import asyncio
import time
from typing import List

from app.schemas import SshResponse
from app.core.config import settings


class SshAccessDeniedError(Exception):
    def __init__(self, host: str, message: str | None):
        super().__init__(f"SSH access denied for {host}: {message}")
        self.host = host
        self.message = message


async def _execute_ssh_command(host, command) -> SshResponse:
    verbose: bool = settings.ENVIRONMENT == "local"
    start_time = time.time()

    ssh_command = f'ssh {host} "{command}"'
    process = await asyncio.create_subprocess_shell(
        ssh_command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    if verbose:
        print(f"{host} {ssh_command}| Awaiting result...")

    stdout, stderr = await process.communicate()

    end_time = time.time()

    execution_time = end_time - start_time
    stdout_output: str | None = (
        stdout.decode().strip() if stdout.decode().strip() != "" else None
    )
    stderr_output: str | None = (
        stderr.decode().strip() if stderr.decode().strip() != "" else None
    )
    filtered_stderr_output = None
    if stderr_output:
        stderr_lines = stderr_output.splitlines()
        filtered_stderr_output = "\n".join(
            line
            for line in stderr_lines
            if not line.lower().startswith("Warning: Permanently added".lower())
        )
    returncode_output: int | None = process.returncode

    if (
        returncode_output != 0
        and filtered_stderr_output
        and "permission denied" in filtered_stderr_output.lower()
    ):
        if verbose:
            print(
                f"Failed to connect {host} over SSH ({execution_time:.2f}s): {filtered_stderr_output or 'No stderr'}"
            )
        raise SshAccessDeniedError(host, filtered_stderr_output)

    if verbose:
        if returncode_output != 0:
            print(
                f"{host} answered FAIL ({execution_time:.2f}s): {filtered_stderr_output or '(no error output)'}"
            )
        else:
            print(
                f"{host} answered OK ({execution_time:.2f}s): {stdout_output or '(no output)'}"
            )

    return {
        "host": host,
        "stdout": stdout_output,
        "stderr": filtered_stderr_output,
        "returncode": returncode_output,
    }


async def execute_ssh_commands_in_batch(server_list, command) -> List[SshResponse]:
    tasks = [_execute_ssh_command(host, command) for host in server_list]
    results = await asyncio.gather(*tasks)
    return results


async def execute_ssh_command(host: str, command: str) -> SshResponse:
    result = await asyncio.gather(_execute_ssh_command(host, command))
    return result[0]
