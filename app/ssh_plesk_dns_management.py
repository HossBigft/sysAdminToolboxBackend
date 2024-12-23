import shlex


from app.host_lists import PLESK_SERVER_LIST
from app.ssh_async_executor import run_command_over_ssh
from app.models import DomainName, SubscriptionName


async def build_restart_dns_service_command(domain: str) -> str:
    escaped_domain = shlex.quote(f'\\"{domain.lower()}\\"')
    return (
        f"plesk bin dns --off {escaped_domain} && plesk bin dns --on {escaped_domain}"
    )


async def restart_dns_service_for_domain(
    host: DomainName, domain: SubscriptionName
) -> None:
    if host in PLESK_SERVER_LIST:
        restart_dns_cmd = await build_restart_dns_service_command(domain=domain)
        run_command_over_ssh(host=host, command=restart_dns_cmd, verbose=True)
    else:
        raise ValueError(f"{host} is not valid Plesk server")
