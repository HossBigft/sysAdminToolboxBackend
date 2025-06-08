from typing import List
from app.core.dependencies import get_token_signer
from app.schemas import SignedExecutorResponse
from app.signed_executor.commands.signed_operation import SignedOperation
from app.signed_executor.async_ssh_handler import (
    execute_ssh_command,
    execute_ssh_commands_in_batch,
)
from app.core_utils.loggers import log_ssh_response, log_ssh_request


async def get_executor_status_from_servers(server_list: List[str]) -> List[SignedExecutorResponse]:
    status_command = "status"

    for i, host in enumerate(server_list):
        log_ssh_request(host, status_command)

    ssh_responses = await execute_ssh_commands_in_batch(
        server_list,
        command=status_command,
    )

    executor_responses: List[SignedExecutorResponse] = []
    for ssh_response in ssh_responses:
        executor_response = SignedExecutorResponse.from_ssh_response(ssh_response)
        execution_time = ssh_response.get("execution_time", 0)
        log_ssh_response(executor_response, execution_time)
        executor_responses.append(executor_response)

    return executor_responses


class SignedExecutorClient:
    def __init__(self):
        self._token_signer = get_token_signer()

    def _sign_operation(self, command_str: str) -> str:
        return "execute " + self._token_signer.create_signed_token(command_str)

    async def execute_on_server(
            self, host: str, operation: SignedOperation, *args: str
    ) -> SignedExecutorResponse:
        command_str = operation.with_args(*args)
        signed_command = self._sign_operation(command_str)

        log_ssh_request(host, signed_command)
        ssh_response = await execute_ssh_command(
            host=host,
            command=signed_command,
        )
        response = SignedExecutorResponse.from_ssh_response(ssh_response)
        log_ssh_response(response , ssh_response["execution_time"])
        return response 

    async def execute_on_servers(
            self, server_list: List[str], command: SignedOperation, *args: str
    ) -> List[SignedExecutorResponse]:
        command_str = command.with_args(*args)
        signed_command = self._sign_operation(command_str)

        for host in server_list:
            log_ssh_request(host, signed_command)

        ssh_responses = await execute_ssh_commands_in_batch(
            server_list,
            command=signed_command,
        )
        executor_responses: List[SignedExecutorResponse] = []
        for ssh_response in ssh_responses:
            executor_response = SignedExecutorResponse.from_ssh_response(ssh_response)
            execution_time = ssh_response.get("execution_time", 0)
            log_ssh_response(executor_response, execution_time)
            executor_responses.append(executor_response)

        return executor_responses
