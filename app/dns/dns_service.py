from fastapi import HTTPException
from typing import Dict, Any
from app.schemas import (
    DNS_SERVER_LIST,
    ExecutionStatus,
    DomainName,
)

from app.signed_executor.signed_executor_client import SignedExecutorClient
from app.signed_executor.commands.dns_command import DNSCommand


class DNSService:
    def __init__(self):
        """Initialize with client and server list."""
        self.client = SignedExecutorClient()
        self.server_list = DNS_SERVER_LIST

    async def remove_zone(self, domain: DomainName) -> None:
        command = DNSCommand.remove_zone()
        await self.client.execute_on_servers(self.server_list, command, domain.name)

    async def get_zone_masters(self, domain: DomainName) -> Dict[str, Any]:
        command = DNSCommand.get_zone_master()
        responses = await self.client.execute_on_servers(
            self.server_list, command, domain.name
        )
        responses = [
            response for response in responses if response.status == ExecutionStatus.OK
        ]
        results = []
        for response in responses:
            if response.payload:
                results.append(
                    {
                        "ns": response.host,
                        "zone_master": response.payload["zonemaster_ip"],
                    }
                )

        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"No DNS zone found  for domain: {domain.name}",
            )

        return {"domain": domain.name, "answers": results}
