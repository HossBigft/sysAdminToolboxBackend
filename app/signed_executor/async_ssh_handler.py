import asyncio
import asyncssh
import time
import statistics
import logging

from typing import List, Callable, Any, Dict

from app.schemas import SshResponse
from app.core.DomainMapper import HOSTS
from app.core.config import settings
from app.core_utils.loggers import get_ssh_logger

logger = get_ssh_logger()

_connection_pool = {}

SSH_LOGIN_TIMEOUT = 3
SSH_EXECUTION_TIMEOUT = 1
MAX_TIMEOUT = 10

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("asyncssh")
logger.setLevel(logging.INFO)


async def run_with_adaptive_timeout(
    coro_factory: Callable[..., Any],
    base_timeout: float = 1.0,
    factor: float = 2.0,
    max_timeout: float = 10.0,
    max_retries: int | None = None,
) -> Any:
    timeout = base_timeout
    attempt = 0

    while timeout <= max_timeout:
        try:
            return await asyncio.wait_for(coro_factory(), timeout=timeout)
        except asyncio.TimeoutError:
            if max_retries is not None:
                attempt += 1
                if attempt > max_retries:
                    raise
            timeout = min(timeout * factor, max_timeout)


async def _create_connection(host: str):
    start = time.time()
    try:
        host_ip = str(HOSTS.resolve_domain(host).ips[0])
        connection = await run_with_adaptive_timeout(
            lambda: asyncssh.connect(
                host_ip,
                username=settings.SSH_USER,
                known_hosts=None,
                login_timeout=SSH_LOGIN_TIMEOUT,
                config=None,
                # optional for tests on wsl
                # client_keys=["../ssh_agent/ssh_key/priv_ed25519.key"]
            ),
            base_timeout=SSH_EXECUTION_TIMEOUT,
            max_timeout=MAX_TIMEOUT,
            max_retries=3,
        )
        _connection_pool[host] = connection
        logger.info(f"Connected to {host} in {time.time() - start}s.")
        return connection
    except asyncio.TimeoutError as e:
        logger.error(f"Connection timed out to {host} in {time.time() - start}s.: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to create connection to {host}: {e}")
        raise


async def initialize_connection_pool(ssh_host_list: List[str]):
    start_time = time.time()
    if not ssh_host_list:
        raise ValueError("No SSH hosts are given to initialize connections with.")

    print(f"Initializing SSH connection pool for {len(ssh_host_list)} hosts...")

    semaphore = asyncio.Semaphore(100)

    async def _create_connection_with_limit(host):
        async with semaphore:
            return await _create_connection(host)

    connection_tasks = []
    for host in ssh_host_list:
        connection_tasks.append(_create_connection_with_limit(host))

    results = await asyncio.gather(*connection_tasks, return_exceptions=True)

    successful_connections = 0
    failed_connections = 0

    for i, result in enumerate(results):
        host = ssh_host_list[i]
        if isinstance(result, Exception):
            logger.error(f"Failed to connect to {host}: {result}")
            failed_connections += 1
        else:
            successful_connections += 1
    end_time = time.time()
    execution_time = end_time - start_time
    print(
        f"Connection pool initialized in {execution_time}s: {successful_connections} successful, {failed_connections} failed"
    )


async def close_all_connections():
    print("Closing all SSH connections...")

    async def _close_single_connection(host: str, connection):
        try:
            connection.close()
            print(f"Closed connection to {host}")
            return True
        except Exception as e:
            logger.error(f"Error closing connection to {host}: {e}")
            return False

    close_tasks = [
        _close_single_connection(host, conn) for host, conn in _connection_pool.items()
    ]
    await asyncio.gather(*close_tasks, return_exceptions=True)

    _connection_pool.clear()
    print("All SSH connections closed")


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
        print(f"Connection to {host} is not found, creating.")
        _connection_pool[host] = await _create_connection(host)
        return _connection_pool[host]


class SshExecutionError(Exception):
    def __init__(self, host: str, message: str | None):
        super().__init__(f"SSH access denied for {host}: {message}")
        self.host = host
        self.message = message


async def _execute_ssh_command(host: str, command: str):
    overall_start = time.time()
    try:
        conn_start = time.time()
        conn = await _get_connection(host)
        conn_time = time.time() - conn_start
        start_time = time.time()
        result = await asyncio.wait_for(
            conn.run(command), timeout=SSH_EXECUTION_TIMEOUT
        )
        end_time = time.time()
        execution_time = end_time - start_time

        process_start = time.time()
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

        process_time = time.time() - process_start
        total_time = time.time() - overall_start
        return {
            "host": host,
            "stdout": stdout_output,
            "stderr": filtered_stderr_output,
            "returncode": result.exit_status,
            "execution_time": total_time,
            "timing_breakdown": {
                "connection_time": conn_time,
                "command_time": execution_time,
                "processing_time": process_time,
                "total_time": total_time,
            },
        }

    except asyncssh.PermissionDenied as e:
        end_time = time.time()
        execution_time = end_time - overall_start
        raise SshExecutionError(host, f"Permission denied: {str(e)}")

    except asyncssh.ConnectionLost as e:
        end_time = time.time()
        execution_time = end_time - overall_start
        raise SshExecutionError(host, f"Connection lost: {str(e)}")

    except asyncssh.TimeoutError as e:
        end_time = time.time()
        execution_time = end_time - overall_start
        raise SshExecutionError(host, f"Connection timed out: {str(e)}")

    except asyncio.TimeoutError as e:
        end_time = time.time()
        execution_time = end_time - overall_start
        raise SshExecutionError(
            host, f"Execution timed out in {SSH_EXECUTION_TIMEOUT}s: {str(e)}"
        )

    except asyncssh.Error as e:
        end_time = time.time()
        execution_time = end_time - overall_start

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
) -> List[SshResponse | Exception]:
    start_time = time.time()
    semaphore = asyncio.Semaphore(100)

    async def worker(host: str):
        async with semaphore:
            try:
                return await run_with_adaptive_timeout(
                    lambda: _execute_ssh_command(host, command),
                    base_timeout=SSH_EXECUTION_TIMEOUT,
                    factor=2,
                    max_timeout=2,
                    max_retries=2,
                )
            except Exception as e:
                return e

    gather_start = time.time()
    results = await asyncio.gather(*(worker(host) for host in server_list))
    gather_time = time.time() - gather_start
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Batch size of {len(server_list)} executed in {execution_time}s.")

    stats = calculate_timing_stats(results)
    outliers = find_outliers(results)

    print(
        f"\nBatch execution completed in {execution_time:.2f}s (gather: {gather_time:.2f}s)"
    )
    log_detailed_stats(stats, outliers)
    return results


async def execute_ssh_command(host: str, command: str) -> SshResponse:
    return await _execute_ssh_command(host, command)


def calculate_timing_stats(
    results: List[Dict[str, Any] | Exception],
) -> Dict[str, Any]:
    """Calculate statistics for different timing components"""

    # Keep only successful dict results
    successful_results = [r for r in results if isinstance(r, dict)]

    if not successful_results:
        return {"error": "No successful results to analyze"}

    total_times = [r["execution_time"] for r in successful_results]
    conn_times = [r["timing_breakdown"]["connection_time"] for r in successful_results]
    cmd_times = [r["timing_breakdown"]["command_time"] for r in successful_results]
    process_times = [
        r["timing_breakdown"]["processing_time"] for r in successful_results
    ]

    def calc_stats(times: List[float], name: str) -> Dict[str, float]:
        return {
            f"{name}_min": min(times),
            f"{name}_max": max(times),
            f"{name}_mean": statistics.mean(times),
            f"{name}_median": statistics.median(times),
            f"{name}_stdev": statistics.stdev(times) if len(times) > 1 else 0.0,
            f"{name}_p95": sorted(times)[int(len(times) * 0.95)]
            if len(times) > 1
            else times[0],
        }

    stats = {}
    stats.update(calc_stats(total_times, "total"))
    stats.update(calc_stats(conn_times, "connection"))
    stats.update(calc_stats(cmd_times, "command"))
    stats.update(calc_stats(process_times, "processing"))

    return {
        "summary": stats,
        "successful_count": len(successful_results),
        "failed_count": len(results) - len(successful_results),
        "total_count": len(results),
    }


def find_outliers(
    results: List[Dict[str, Any] | Exception], threshold_multiplier: float = 2.0
) -> Dict[str, List[Dict[str, Any]]]:
    """Find hosts that are significantly slower than average"""

    successful_results = [r for r in results if isinstance(r, dict)]
    if len(successful_results) < 2:
        return {"outliers": []}

    total_times = [r["execution_time"] for r in successful_results]
    mean_time = statistics.mean(total_times)
    stdev_time = statistics.stdev(total_times)
    threshold = mean_time + (threshold_multiplier * stdev_time)

    outliers = {"slow_hosts": [], "fast_hosts": [], "failed_hosts": []}

    for r in results:
        if isinstance(r, dict):
            if r["execution_time"] > threshold:
                outliers["slow_hosts"].append(
                    {
                        "host": r["host"],
                        "time": r["execution_time"],
                        "breakdown": r["timing_breakdown"],
                    }
                )
            elif r["execution_time"] < (mean_time - stdev_time):
                outliers["fast_hosts"].append(
                    {
                        "host": r["host"],
                        "time": r["execution_time"],
                    }
                )
        elif isinstance(r, SshExecutionError):
            outliers["failed_hosts"].append(
                {
                    "host": r.host,
                    "time": None,
                    "error": r.message,
                }
            )
        elif isinstance(r, Exception):
            outliers["failed_hosts"].append(
                {
                    "host": "Unknown",
                    "time": None,
                    "error": str(r),
                }
            )

    return outliers


def log_detailed_stats(stats: Dict[str, Any], outliers: Dict[str, List]):
    """Log comprehensive timing statistics"""

    if "error" in stats:
        print(f"Stats calculation failed: {stats['error']}")
        return

    summary = stats["summary"]

    # Overall summary
    print("=" * 60)
    print("BATCH EXECUTION STATISTICS")
    print("=" * 60)
    print(f"Total requests: {stats['total_count']}")
    print(f"Successful: {stats['successful_count']}")
    print(f"Failed: {stats['failed_count']}")
    print(
        f"Success rate: {stats['successful_count'] / stats['total_count'] * 100:.1f}%"
    )

    # Timing breakdown
    categories = ["total", "connection", "command", "processing"]

    for category in categories:
        print(f"\n{category.upper()} TIMES:")
        print(f"  Min:     {summary[f'{category}_min']:.3f}s")
        print(f"  Max:     {summary[f'{category}_max']:.3f}s")
        print(f"  Mean:    {summary[f'{category}_mean']:.3f}s")
        print(f"  Median:  {summary[f'{category}_median']:.3f}s")
        print(f"  StdDev:  {summary[f'{category}_stdev']:.3f}s")
        print(f"  95th %:  {summary[f'{category}_p95']:.3f}s")

    if outliers.get("slow_hosts"):
        print(f"\nSLOW HOSTS ({len(outliers['slow_hosts'])} hosts):")
        for host_info in outliers["slow_hosts"]:
            print(
                f"  {host_info['host']}: {host_info['time']:.3f}s "
                f"(conn: {host_info['breakdown']['connection_time']:.3f}s, "
                f"cmd: {host_info['breakdown']['command_time']:.3f}s)"
            )

    if outliers.get("failed_hosts"):
        print(f"\nFAILED HOSTS ({len(outliers['failed_hosts'])} hosts):")
        for host_info in outliers["failed_hosts"]:
            print(f"  {host_info['host']}: - {host_info['error']}")

    print("=" * 60)
