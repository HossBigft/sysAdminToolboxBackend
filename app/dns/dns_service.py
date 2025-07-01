import asyncio
import aiodns

from fastapi import HTTPException
from tldextract import extract

from app.dns.dns_models import ZoneMaster
from app.schemas import (
    DNS_SERVER_LIST,
    ExecutionStatus,
    DomainName,
)

from app.signed_executor.signed_executor_client import SignedExecutorClient
from app.signed_executor.commands.dns_operation import DNSOperation
from app.core.DomainMapper import HOSTS
from app.core.config import settings
from app.dns.dns_resolver import DNSResolver

GOOGLE_DNS = ["8.8.8.8", "8.8.4.4"]


PUBLIC_DNS = [
    {"name": "Google", "ip": "8.8.8.8"},
    {"name": "OpenDNS", "ip": "208.67.222.220"},
    {"name": "OpenDNS", "ip": "208.67.222.220"},
    {"name": "Quad9", "ip": "9.9.9.9"},
    {"name": "Oracle Corporation", "ip": "216.146.35.35"},
    {"name": "WholeSale Internet, Inc.", "ip": "204.12.225.227"},
    {"name": "Aureon Network Services", "ip": "207.177.68.4"},
    {"name": "NeuStar", "ip": "156.154.70.64"},
    {"name": "Fortinet Inc", "ip": "208.91.112.53"},
    {"name": "Skydns", "ip": "195.46.39.39"},
    {"name": "Liquid Telecommunications Ltd", "ip": "5.11.11.11"},
    {"name": "Tele2 Nederland B.V.", "ip": "87.213.100.113"},
    {"name": "Completel SAS", "ip": "83.145.86.7"},
    {"name": "Prioritytelecom Spain S.A", "ip": "212.230.255.1"},
    {"name": "nemox.net", "ip": "83.137.41.9"},
    {"name": "Deutsche Telekom AG", "ip": "195.243.214.4"},
    {"name": "Marcatel Com", "ip": "200.56.224.11"},
    {"name": "Claro S.A", "ip": "200.248.178.54"},
    {"name": "TT Dotcom Sdn Bhd", "ip": "211.25.206.147"},
    {"name": "Cloudflare Inc", "ip": "1.1.1.1"},
    {"name": "Pacific Internet", "ip": "61.8.0.113"},
    {"name": "Global-Gateway Interne", "ip": "122.56.107.86"},
    {"name": "DigitalOcean LLC", "ip": "139.59.219.245"},
    {"name": "LG Dacom Corporation", "ip": "164.124.101.2"},
    {"name": "Teknet Yazlim", "ip": "31.7.37.37"},
    {"name": "Kappa Internet Services Private Limited", "ip": "115.178.96.2"},
    {"name": "CMPak Limited", "ip": "209.150.154.1"},
    {"name": "Indigo", "ip": "194.125.133.10"},
    {"name": "SS Online", "ip": "103.80.1.2"},
]


def _get_internal_nameservers() -> list[str]:
    return [
        str(HOSTS.resolve_domain(nameserver).ips[0])
        for nameserver in settings.DNS_SLAVE_SERVERS.keys()
    ]


async def get_ns_records(domain: str, ns_ip: str):
    ns_resolver = aiodns.DNSResolver(timeout=2)
    ns_resolver.nameservers = [ns_ip]
    result = await ns_resolver.query(domain, "NS")
    return sorted(str(r.host).rstrip(".") for r in result)


class DNSService:
    def __init__(self):
        self.client = SignedExecutorClient()
        self.server_list = DNS_SERVER_LIST
        self.google_resolver = DNSResolver(GOOGLE_DNS)
        self.internal_resolver = DNSResolver(_get_internal_nameservers())

    async def remove_zone(self, domain: DomainName) -> None:
        command = DNSOperation.remove_zone()
        await self.client.execute_on_servers(self.server_list, command, domain.name)

    async def get_zone_masters(self, domain: DomainName) -> list[ZoneMaster]:
        command = DNSOperation.get_zone_master()
        responses = await self.client.execute_on_servers(
            self.server_list, command, domain.name
        )
        responses = [
            response for response in responses if response.status == ExecutionStatus.OK
        ]
        zone_masters: list[ZoneMaster] = []
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

    async def resolve_authoritative_ns_record(self, domain: str) -> list[str] | None:
        try:
            google_resolver = aiodns.DNSResolver(nameservers=GOOGLE_DNS)

            top_level_domain = extract(domain).registered_domain
            if not top_level_domain:
                return None

            soa_record = await google_resolver.query(top_level_domain, "SOA")
            primary_ns = str(soa_record.nsname).rstrip(".")

            ns_ip_result = await google_resolver.query(primary_ns, "A")
            primary_ns_ip = str(ns_ip_result[0].host)

            auth_resolver = aiodns.DNSResolver(nameservers=[primary_ns_ip])
            ns_records = await auth_resolver.query(domain, "NS")
            return sorted([str(r.host) for r in ns_records])

        except aiodns.error.DNSError:
            return None

    async def get_ns_records_from_public_ns(
        self, domain: str
    ) -> dict[str, dict[str, list[str]]]:
        async def get_ns_records(domain: str, ns_ip: str) -> list[str]:
            ns_resolver = aiodns.DNSResolver(timeout=2)
            ns_resolver.nameservers = [ns_ip]
            result = await ns_resolver.query(domain, "NS")
            return sorted(str(r.host).rstrip(".") for r in result)

        tasks = [
            get_ns_records(domain, ns_ip=nameserver["ip"]) for nameserver in PUBLIC_DNS
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        ns_dict = {}
        for nameserver, result in zip(PUBLIC_DNS, results):
            ns_dict[nameserver["name"]] = result

        return ns_dict
