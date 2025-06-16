import asyncio
import asyncssh
import time

from typing import List

from app.schemas import SshResponse
from app.core.DomainMapper import HOSTS
from app.core.config import settings
from app.core_utils.loggers import get_ssh_logger

logger = get_ssh_logger()

_connection_pool = {}

SSH_LOGIN_TIMEOUT = 3
SSH_EXECUTION_TIMEOUT = 1


async def _create_connection(host: str):
    try:
        host_ip = str(HOSTS.resolve_domain(host).ips[0])
        connection = await asyncssh.connect(
            host_ip,
            username=settings.SSH_USER,
            known_hosts=None,
            login_timeout=SSH_LOGIN_TIMEOUT,
        )
        _connection_pool[host] = connection
        return connection
    except Exception as e:
        logger.error(f"Failed to create connection to {host}: {e}")
        raise


async def initialize_connection_pool(ssh_host_list: List[str]):
    if not ssh_host_list:
        raise ValueError("No SSH hosts are given to initialize connections with.")

    logger.info(f"Initializing SSH connection pool for {len(ssh_host_list)} hosts...")

    connection_tasks = []
    for host in ssh_host_list:
        connection_tasks.append(_create_connection(host))

    results = await asyncio.gather(*connection_tasks, return_exceptions=True)

    successful_connections = 0
    failed_connections = 0

    for i, result in enumerate(results):
        host = ssh_host_list[i]
        if isinstance(result, Exception):
            logger.error(f"Failed to connect to {host}: {result}")
            failed_connections += 1
        else:
            logger.info(f"Successfully connected to {host}")
            successful_connections += 1

    logger.info(
        f"Connection pool initialized: {successful_connections} successful, {failed_connections} failed"
    )


async def close_all_connections():
    logger.info("Closing all SSH connections...")

    async def _close_single_connection(host: str, connection):
        try:
            connection.close()
            logger.info(f"Closed connection to {host}")
            return True
        except Exception as e:
            logger.error(f"Error closing connection to {host}: {e}")
            return False

    close_tasks = [
        _close_single_connection(host, conn) for host, conn in _connection_pool.items()
    ]
    await asyncio.gather(*close_tasks, return_exceptions=True)

    _connection_pool.clear()
    logger.info("All SSH connections closed")


async def _get_connection(host: str):
    if host in _connection_pool.keys():
        conn = _connection_pool[host]
        if conn.is_closed():
            logger.warning(f"Connection to {host} is dead, recreating...")
            _connection_pool[host] = await _create_connection(host)
            return _connection_pool[host]
        else:
            return conn
    else:
        _connection_pool[host] = await _create_connection(host)
        return _connection_pool[host]


class SshExecutionError(Exception):
    def __init__(self, host: str, message: str | None):
        super().__init__(f"SSH access denied for {host}: {message}")
        self.host = host
        self.message = message


async def _execute_ssh_command(host: str, command: str) -> SshResponse:
    try:
        conn = await _get_connection(host)
        start_time = time.time()
        result = await asyncio.wait_for(
            conn.run(command), timeout=SSH_EXECUTION_TIMEOUT
        )
        end_time = time.time()
        execution_time = end_time - start_time

        stdout_output: str | None = (
            result.stdout.strip()
            if result.stdout and result.stdout.strip() != ""
            else None
        )
        stderr_output: str | None = (
            result.stderr.strip()
            if result.stderr and result.stderr.strip() != ""
            else None
        )

        filtered_stderr_output = None
        if stderr_output:
            stderr_lines = stderr_output.splitlines()
            filtered_stderr_output = "\n".join(
                line
                for line in stderr_lines
                if not line.lower().startswith("Warning: Permanently added".lower())
            )
            filtered_stderr_output = (
                filtered_stderr_output if filtered_stderr_output.strip() else None
            )

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
        raise SshExecutionError(host, f"Permission denied: {str(e)}")

    except asyncssh.ConnectionLost as e:
        end_time = time.time()
        execution_time = end_time - start_time
        raise SshExecutionError(host, f"Connection lost: {str(e)}")

    except asyncssh.TimeoutError as e:
        end_time = time.time()
        execution_time = end_time - start_time
        raise SshExecutionError(host, f"Connection timed out: {str(e)}")

    except asyncio.TimeoutError as e:
        end_time = time.time()
        execution_time = end_time - start_time
        raise SshExecutionError(
            host, f"Execution timed out in {SSH_EXECUTION_TIMEOUT}s: {str(e)}"
        )

    except asyncssh.Error as e:
        end_time = time.time()
        execution_time = end_time - start_time

        error_message = str(e).lower()
        if (
            "permission denied" in error_message
            or "authentication failed" in error_message
        ):
            raise SshExecutionError(host, str(e))

        return {
            "host": host,
            "stdout": None,
            "stderr": str(e),
            "returncode": -1,
            "execution_time": execution_time,
        }


async def execute_ssh_commands_in_batch(
    server_list: List[str], command: str
) -> List[SshResponse | BaseException]:
    tasks = [_execute_ssh_command(host, command) for host in server_list]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    return results


async def execute_ssh_command(host: str, command: str) -> SshResponse:
    return await _execute_ssh_command(host, command)
