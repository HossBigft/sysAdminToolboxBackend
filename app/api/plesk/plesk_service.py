from fastapi import HTTPException
from typing import List, Dict, Any
from app.schemas import (
    PLESK_SERVER_LIST,
    PleskServerDomain,
    SubscriptionName,
    DomainName,
    ExecutionStatus,
    LinuxUsername,
)
from app.api.plesk.plesk_schemas import SubscriptionDetailsModel, TestMailData
from app.signed_executor.signed_executor_client import SignedExecutorClient
from app.signed_executor.commands.plesk_command import PleskCommand
from app.core.DomainMapper import HOSTS


class PleskService:
    def __init__(self):
        self.client = SignedExecutorClient()
        self.server_list = PLESK_SERVER_LIST

    async def fetch_subscription_id_by_domain(
        self, host: PleskServerDomain, domain: SubscriptionName
    ) -> Dict[str, Any] | None:
        command = PleskCommand.get_subscription_id_by_domain()
        response = await self.client.execute_on_server(host.name, command, domain.name)
        return response.payload if response and response.payload else None

    async def is_domain_exist_on_server(
        self, host: PleskServerDomain, domain: SubscriptionName
    ) -> bool:
        return await self.fetch_subscription_id_by_domain(host, domain) is not None

    async def restart_dns_service_for_domain(
        self, host: PleskServerDomain, domain: SubscriptionName
    ) -> None:
        command = PleskCommand.restart_dns_service()
        await self.client.execute_on_server(host.name, command, domain.name)

    async def fetch_subscription_info(
        self, domain: DomainName
    ) -> List[SubscriptionDetailsModel]:
        command = PleskCommand.fetch_subscription_info()
        responses = await self.client.execute_on_servers(
            self.server_list, command, domain.name
        )

        responses = [
            response
            for response in responses
            if response.status is not ExecutionStatus.NOT_FOUND
        ]

        if not responses:
            raise HTTPException(
                status_code=404,
                detail=f"No subscription information found for domain: {domain.name}",
            )

        results = []
        for response in responses:
            host_name = response.host
            if response.payload:
                for item in response.payload:
                    model_data = {"host": HOSTS.resolve_domain(host_name), **item}
                    model = SubscriptionDetailsModel.model_validate(model_data)
                    results.append(model)
        return results

    async def generate_subscription_login_link(
        self, host: PleskServerDomain, subscription_id: int, ssh_username: LinuxUsername
    ) -> str:
        command = PleskCommand.get_login_link()
        response = await self.client.execute_on_server(
            host.name, command, str(subscription_id), str(ssh_username)
        )

        if response.status == ExecutionStatus.NOT_FOUND:
            raise HTTPException(
                status_code=404,
                detail=f"Subscription with ID {subscription_id} not found",
            )

        if not response.payload:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate login link",
            )

        return response.payload["login_link"]

    async def get_testmail_login_data(
        self, host: PleskServerDomain, mail_domain: SubscriptionName
    ) -> TestMailData:
        command = PleskCommand.get_testmail_credentials()
        response = await self.client.execute_on_server(
            host.name, command, mail_domain.name
        )

        if not response or not response.payload:
            raise HTTPException(
                status_code=404,
                detail=f"No subscription found for mail domain: {mail_domain.name}",
            )

        return TestMailData.model_validate(response.payload)
