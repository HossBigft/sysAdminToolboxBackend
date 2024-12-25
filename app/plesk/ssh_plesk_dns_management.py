import shlex


from app.host_lists import PLESK_SERVER_LIST
from app.AsyncSSHandler import execute_ssh_command
from app.plesk.models import DomainName, SubscriptionName


class PleskServiceError(Exception):
    """Base exception for Plesk service operations"""

    pass


class DomainNotFoundError(PleskServiceError):
    """Raised when domain doesn't exist on server"""

    pass


class CommandExecutionError(PleskServiceError):
    """Raised when command execution fails"""

    def __init__(self, stderr: str, return_code: int):
        self.stderr = stderr
        self.return_code = return_code
        super().__init__(f"Command failed with return code {return_code}: {stderr}")


async def build_restart_dns_service_command(domain: DomainName) -> str:
    escaped_domain = shlex.quote(f'\\"{domain.domain.lower()}\\"')
    return (
        f"plesk bin dns --off {escaped_domain} && plesk bin dns --on {escaped_domain}"
    )


async def is_domain_exist_on_server(host: DomainName, domain: SubscriptionName) -> bool:
    get_subscription_name_cmd = f'plesk db -Ne "SELECT name FROM domains WHERE webspace_id=0 AND id={domain.domain}"'
    result = await execute_ssh_command(host.domain, get_subscription_name_cmd)
    subscription_name = result["stdout"]
    return not subscription_name == ""

async def restart_dns_service_for_domain(
    host: DomainName, domain: SubscriptionName
) -> None:
    if host in PLESK_SERVER_LIST:
        restart_dns_cmd = await build_restart_dns_service_command(domain=domain.domain)
        result = await execute_ssh_command(
            host=host.domain, command=restart_dns_cmd, verbose=True
        )
        match result["returncode"]:
            case "4":
                raise DomainNotFoundError(f"Domain {domain.domain} does not exist on server")
            case "0":
                pass
            case _:
                raise CommandExecutionError(
                    stderr=result["stderr"], returncode=["returncode"]
                )

    else:
        raise ValueError(f"{host.domain} is not valid Plesk server")
    

