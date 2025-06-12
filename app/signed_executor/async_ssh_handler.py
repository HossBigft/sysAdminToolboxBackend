import asyncio
import asyncssh
import time
import statistics
from typing import List, Dict, Any

from app.schemas import SshResponse
from app.core.DomainMapper import HOSTS
from app.core.config import settings


_connection_pool = {}

SSH_LOGIN_TIMEOUT=3

async def _get_connection(host: str):
    start = time.time()
    if host in _connection_pool.keys():
        conn_time = time.time() - start 
        print(f"Finding connection to {host} took {conn_time:.2f}s")
        return _connection_pool[host]
    else:
        host_ip = str(HOSTS.resolve_domain(host).ips[0])
        _connection_pool[host] = await asyncssh.connect(host_ip, username=settings.SSH_USER, known_hosts=None, login_timeout=SSH_LOGIN_TIMEOUT)
        conn_time = time.time() - start
        print(f"Connection to {host} took {conn_time:.2f}s")
        return _connection_pool[host]


class SshAccessDeniedError(Exception):
    def __init__(self, host: str, message: str | None):
        super().__init__(f"SSH access denied for {host}: {message}")
        self.host = host
        self.message = message


async def _execute_ssh_command(host: str, command: str) -> Dict[str, Any]:
    overall_start = time.time()
    
    try:
        # Time connection establishment
        conn_start = time.time()
        conn = await _get_connection(host)
        conn_time = time.time() - conn_start
        
        # Time command execution
        cmd_start = time.time()
        result = await conn.run(command)
        cmd_time = time.time() - cmd_start
        
        # Time output processing
        process_start = time.time()
        stdout_output = (
            result.stdout.strip() if result.stdout and result.stdout.strip() != "" else None
        )
        stderr_output = (
            result.stderr.strip() if result.stderr and result.stderr.strip() != "" else None
        )
        
        filtered_stderr_output = None
        if stderr_output:
            stderr_lines = stderr_output.splitlines()
            filtered_stderr_output = "\n".join(
                line for line in stderr_lines
                if not line.lower().startswith("Warning: Permanently added".lower())
            )
            filtered_stderr_output = filtered_stderr_output if filtered_stderr_output.strip() else None
        
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
                "command_time": cmd_time,
                "processing_time": process_time,
                "total_time": total_time
            }
        }
    
    except Exception as e:
        total_time = time.time() - overall_start
        print(f"Host {host} failed after {total_time:.2f}s: {e}")
        # Return error info with timing
        return {
            "host": host,
            "stdout": None,
            "stderr": str(e),
            "returncode": -1,
            "execution_time": total_time,
            "timing_breakdown": {
                "connection_time": 0,
                "command_time": 0,
                "processing_time": 0,
                "total_time": total_time
            },
            "error": True
        }

def calculate_timing_stats(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Calculate statistics for different timing components"""
    
    # Filter out failed requests for clean stats
    successful_results = [r for r in results if not r.get('error', False)]
    
    if not successful_results:
        return {"error": "No successful results to analyze"}
    
    # Extract timing data
    total_times = [r['execution_time'] for r in successful_results]
    conn_times = [r['timing_breakdown']['connection_time'] for r in successful_results]
    cmd_times = [r['timing_breakdown']['command_time'] for r in successful_results]
    process_times = [r['timing_breakdown']['processing_time'] for r in successful_results]
    
    def calc_stats(times: List[float], name: str) -> Dict[str, float]:
        return {
            f"{name}_min": min(times),
            f"{name}_max": max(times),
            f"{name}_mean": statistics.mean(times),
            f"{name}_median": statistics.median(times),
            f"{name}_stdev": statistics.stdev(times) if len(times) > 1 else 0.0,
            f"{name}_p95": sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0]
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
        "total_count": len(results)
    }

def find_outliers(results: List[Dict[str, Any]], threshold_multiplier: float = 2.0) -> Dict[str, List[str]]:
    """Find hosts that are significantly slower than average"""
    
    successful_results = [r for r in results if not r.get('error', False)]
    if len(successful_results) < 2:
        return {"outliers": []}
    
    total_times = [r['execution_time'] for r in successful_results]
    mean_time = statistics.mean(total_times)
    stdev_time = statistics.stdev(total_times)
    threshold = mean_time + (threshold_multiplier * stdev_time)
    
    outliers = {
        "slow_hosts": [],
        "fast_hosts": [],
        "failed_hosts": []
    }
    
    for result in results:
        if result.get('error', False):
            outliers["failed_hosts"].append({
                "host": result['host'],
                "time": result['execution_time'],
                "error": result.get('stderr', 'Unknown error')
            })
        elif result['execution_time'] > threshold:
            outliers["slow_hosts"].append({
                "host": result['host'],
                "time": result['execution_time'],
                "breakdown": result['timing_breakdown']
            })
        elif result['execution_time'] < (mean_time - stdev_time):
            outliers["fast_hosts"].append({
                "host": result['host'],
                "time": result['execution_time']
            })
    
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
    print(f"Success rate: {stats['successful_count']/stats['total_count']*100:.1f}%")
    
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
    
    # Outliers
    if outliers["slow_hosts"]:
        print(f"\nSLOW HOSTS ({len(outliers['slow_hosts'])} hosts):")
        for host_info in outliers["slow_hosts"]:
            print(f"  {host_info['host']}: {host_info['time']:.3f}s "
                          f"(conn: {host_info['breakdown']['connection_time']:.3f}s, "
                          f"cmd: {host_info['breakdown']['command_time']:.3f}s)")
    
    if outliers["failed_hosts"]:
        print(f"\nFAILED HOSTS ({len(outliers['failed_hosts'])} hosts):")
        for host_info in outliers["failed_hosts"]:
            print(f"  {host_info['host']}: {host_info['time']:.3f}s - {host_info['error']}")
    
    print("=" * 60)

async def execute_ssh_commands_in_batch(server_list: List[str], command: str) -> List[Dict[str, Any]]:
    batch_start = time.time()
    print(f"Starting batch execution for {len(server_list)} hosts")
    print(f"Command: {command}")
    
    tasks = [_execute_ssh_command(host, command) for host in server_list]
    
    # Time the gather operation
    gather_start = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=False)
    gather_time = time.time() - gather_start
    
    total_time = time.time() - batch_start
    
    # Calculate and log statistics
    stats = calculate_timing_stats(results)
    outliers = find_outliers(results)
    
    print(f"\nBatch execution completed in {total_time:.2f}s (gather: {gather_time:.2f}s)")
    log_detailed_stats(stats, outliers)
    
    return results

# Example usage with additional helper function
def get_timing_summary(results: List[Dict[str, Any]]) -> str:
    """Get a quick one-liner summary of timing"""
    stats = calculate_timing_stats(results)
    if "error" in stats:
        return "No timing data available"
    
    s = stats["summary"]
    return (f"Batch: {len(results)} hosts, "
            f"Times: {s['total_min']:.2f}s-{s['total_max']:.2f}s "
            f"(avg: {s['total_mean']:.2f}s, median: {s['total_median']:.2f}s)")


async def execute_ssh_command(host: str, command: str) -> SshResponse:
    return await _execute_ssh_command(host, command)
