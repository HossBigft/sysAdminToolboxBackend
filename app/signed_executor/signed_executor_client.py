from typing import List
from app.core.dependencies import get_token_signer
from app.schemas import SignedExecutorResponse
from app.signed_executor.commands.signed_command import SignedCommand
from app.signed_executor.async_ssh_handler import execute_ssh_command, execute_ssh_commands_in_batch


class SignedExecutorClient:

    def __init__(self):
        self._token_signer = get_token_signer()

    def _sign_command(self, command_str: str) -> str:

        return "execute " + self._token_signer.create_signed_token(command_str)

    async def execute_on_server(
        self, host: str, command: SignedCommand, *args: str
    ) -> SignedExecutorResponse:

        command_str = command.with_args(*args)
        signed_command = self._sign_command(command_str)

        ssh_response = await execute_ssh_command(
            host=host,
            command=signed_command,
        )
        return SignedExecutorResponse.from_ssh_response(ssh_response)

    async def execute_on_servers(
        self, server_list: List[str], command: SignedCommand, *args: str
    ) -> List[SignedExecutorResponse]:

        command_str = command.with_args(*args)
        signed_command = self._sign_command(command_str)

        ssh_responses = await execute_ssh_commands_in_batch(
            server_list,
            command=signed_command,
        )
        return [
            SignedExecutorResponse.from_ssh_response(response)
            for response in ssh_responses
        ]
