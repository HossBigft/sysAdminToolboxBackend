from fastapi import HTTPException
from typing import  List

from app.dns.dns_models import  ZoneMaster
from app.schemas import (
    DNS_SERVER_LIST,
    ExecutionStatus,
    DomainName,
)

from app.signed_executor.signed_executor_client import SignedExecutorClient
from app.signed_executor.commands.dns_operation import DNSOperation


class DNSService:
    def __init__(self):
        """Initialize with client and server list."""
        self.client = SignedExecutorClient()
        self.server_list = DNS_SERVER_LIST

    async def remove_zone(self, domain: DomainName) -> None:
        command = DNSOperation.remove_zone()
        await self.client.execute_on_servers(self.server_list, command, domain.name)

    async def get_zone_masters(self, domain: DomainName) -> List[ZoneMaster]:
        command = DNSOperation.get_zone_master()
        responses = await self.client.execute_on_servers(
            self.server_list, command, domain.name
        )
        responses = [
            response for response in responses if response.status == ExecutionStatus.OK
        ]
        zone_masters: List[ZoneMaster] = []
        for response in responses:
            if response.payload:
                zone_masters.append(
                    ZoneMaster(host=response.host, ip=response.payload["zonemaster_ip"])
                )

        if not zone_masters:
            raise HTTPException(
                status_code=404,
                detail=f"No DNS zone found  for domain: {domain.name}",
            )

        return zone_masters
