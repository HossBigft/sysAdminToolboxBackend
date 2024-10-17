import asyncio
import shlex


async def _run_command_over_ssh(host, command, verbose: bool):
    sanitized_host = shlex.quote(host)
    sanitized_command = shlex.quote(command)

    ssh_command = (
        f"ssh  -o PasswordAuthentication=no  {sanitized_host} {sanitized_command}"
    )
    process = await asyncio.create_subprocess_shell(
        ssh_command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    if verbose:
        print(f"{host} {ssh_command}| Awaiting result...")
    stdout, stderr = await process.communicate()
    if verbose:
        succesfulAnswer = stdout.decode().strip().rstrip()
        failAnswer = stderr.decode().strip().rstrip()
        if failAnswer:
            print(f"{host} failed: {failAnswer}")
        else:
            print(f"{host} answered: {succesfulAnswer}")

    return (host, stdout.decode().strip(), stderr.decode().strip(), process.returncode)


async def batch_ssh_command_prepare(server_list, command, verbose: bool):
    tasks = [_run_command_over_ssh(host, command, verbose) for host in server_list]
    results = await asyncio.gather(*tasks)
    return [
        {"host": host, "stdout": stdout, "stderr": stderr}
        for host, stdout, stderr, *_ in results
    ]


def batch_ssh_command_result(server_list, command, verbose=False):
    return asyncio.run(batch_ssh_command_prepare(server_list, command, verbose))
