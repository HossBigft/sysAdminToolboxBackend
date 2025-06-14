import asyncio
import asyncssh
import time

from typing import List

from app.schemas import SshResponse
from app.core.DomainMapper import HOSTS
from app.core.config import settings


_connection_pool = {}

SSH_LOGIN_TIMEOUT=3

async def _get_connection(host: str):
    if host in _connection_pool.keys():
        return _connection_pool[host]
    else:
        host_ip = str(HOSTS.resolve_domain(host).ips[0])
        _connection_pool[host] = await asyncssh.connect(host_ip, username=settings.SSH_USER, known_hosts=None, login_timeout=SSH_LOGIN_TIMEOUT)
        return _connection_pool[host]


class SshAccessDeniedError(Exception):
    def __init__(self, host: str, message: str | None):
        super().__init__(f"SSH access denied for {host}: {message}")
        self.host = host
        self.message = message


async def _execute_ssh_command(host: str, command: str) -> SshResponse:
    try:
        conn = await _get_connection(host)
        start_time = time.time()
        result = await conn.run(command)
        end_time = time.time()
        execution_time = end_time - start_time

        stdout_output: str | None = (
            result.stdout.strip() if result.stdout and result.stdout.strip() != "" else None
        )
        stderr_output: str | None = (
            result.stderr.strip() if result.stderr and result.stderr.strip() != "" else None
        )

        filtered_stderr_output = None
        if stderr_output:
            stderr_lines = stderr_output.splitlines()
            filtered_stderr_output = "\n".join(
                line
                for line in stderr_lines
                if not line.lower().startswith("Warning: Permanently added".lower())
            )
            filtered_stderr_output = filtered_stderr_output if filtered_stderr_output.strip() else None

        returncode_output: int | None = result.exit_status

        return {
            "host": host,
            "stdout": stdout_output,
            "stderr": filtered_stderr_output,
            "returncode": returncode_output,
            "execution_time": execution_time,
        }

    except asyncssh.PermissionDenied as e:
        end_time = time.time()
        execution_time = end_time - start_time
        raise SshAccessDeniedError(host, f"Permission denied: {str(e)}")

    except asyncssh.ConnectionLost as e:
        end_time = time.time()
        execution_time = end_time - start_time
        raise SshAccessDeniedError(host, f"Connection lost: {str(e)}")

    except asyncssh.TimeoutError as e:
        end_time = time.time()
        execution_time = end_time - start_time
        raise SshAccessDeniedError(host, f"Connection timed out: {str(e)}")

    except asyncssh.Error as e:
        end_time = time.time()
        execution_time = end_time - start_time

        error_message = str(e).lower()
        if "permission denied" in error_message or "authentication failed" in error_message:
            raise SshAccessDeniedError(host, str(e))

        return {
            "host": host,
            "stdout": None,
            "stderr": str(e),
            "returncode": -1,
            "execution_time": execution_time,
        }


async def execute_ssh_commands_in_batch(server_list: List[str], command: str) -> List[SshResponse]:
    tasks = [_execute_ssh_command(host, command) for host in server_list]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            raise result
        processed_results.append(result)
    
    return processed_results


async def execute_ssh_command(host: str, command: str) -> SshResponse:
    return await _execute_ssh_command(host, command)
