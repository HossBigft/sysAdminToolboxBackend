import enum
from typing import List

from app.api.dependencies import get_token_signer
from app.signed_executor.async_ssh_handler import execute_ssh_command, execute_ssh_commands_in_batch
from app.schemas import (
    DomainName,
    SignedExecutorResponse,
    PleskServerDomain,
    LinuxUsername,
    PLESK_SERVER_LIST,
)


class Operation:
    class PLESK(str, enum.Enum):
        GET_LOGIN_LINK = "GET_LOGIN_LINK"
        FETCH_SUBSCRIPTION_INFO = "FETCH_SUBSCRIPTION_INFO"
        GET_TESTMAIL_CREDENTIALS = "GET_TESTMAIL_CREDENTIALS"
        RESTART_DNS_SERVICE = "RESTART_DNS_SERVICE"
        GET_SUBSCRIPTION_ID_BY_DOMAIN = "GET_SUBSCRIPTION_ID_BY_DOMAIN"

        def __str__(self) -> str:
            return f"PLESK.{self.value}"

    class NS(str, enum.Enum):
        REMOVE_ZONE = "REMOVE_ZONE"
        GET_ZONE_MASTER = "GET_ZONE_MASTER"

        def __str__(self) -> str:
            return f"NS.{self.value}"


class SignedExecutor:
    def __init__(self) -> None:
        self._token_signer = get_token_signer()

    def _sign(self, command: str) -> str:
        return self._token_signer.create_signed_token(command)

    def sign_command(self, operation: Operation, *args: str) -> str:
        base_command = str(operation)
        if args:
            base_command += " " + " ".join(args)
        return "execute " + self._sign(base_command)

    async def plesk_get_login_link_by_sybscription_id(
        self, host: PleskServerDomain, subscription_id: int, ssh_username: LinuxUsername
    ) -> SignedExecutorResponse:
        ssh_response = await execute_ssh_command(
            host.name,
            command=self.sign_command(
                Operation.PLESK.GET_LOGIN_LINK, str(subscription_id), str(ssh_username)
            ),
        )
        login_link_response = SignedExecutorResponse.from_ssh_response(ssh_response)
        return login_link_response

    async def plesk_fetch_subscription_info_by_domain(
        self, domain: DomainName
    ) -> List[SignedExecutorResponse]:
        ssh_responses = await execute_ssh_commands_in_batch(
            PLESK_SERVER_LIST,
            command=self.sign_command(
                Operation.PLESK.FETCH_SUBSCRIPTION_INFO, domain.name
            ),
        )

        return map(SignedExecutorResponse.from_ssh_response, ssh_responses)
