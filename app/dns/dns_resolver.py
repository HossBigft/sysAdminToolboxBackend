import aiodns
import asyncio

from tldextract import extract

from typing import List

from app.core.DomainMapper import HOSTS
from app.core.config import settings

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


class DNSResolver:
    def __init__(self, nameservers: List[str]):
        self.resolver = aiodns.DNSResolver(timeout=2)
        self.resolver.nameservers = nameservers
        self.nameservers = nameservers

    async def resolve_a(self, domain: str) -> List[str] | None:
        try:
            result = await self.resolver.query(domain, "A")
            return [str(r.host) for r in result]
        except aiodns.error.DNSError:
            return None

    async def resolve_ptr(self, ip_address: str) -> List[str] | None:
        try:
            result = await self.resolver.gethostbyaddr(ip_address)
            return [str(result.name)] if result.name else None
        except aiodns.error.DNSError:
            return None

    async def resolve_mx(self, domain: str) -> List[str] | None:
        try:
            result = await self.resolver.query(domain, "MX")
            return [str(r.host) for r in result]
        except aiodns.error.DNSError:
            return None

    async def resolve_ns(self, domain: str) -> List[str] | None:
        try:
            result = await self.resolver.query(domain, "NS")
            return sorted([str(r.host) for r in result])
        except aiodns.error.DNSError:
            return None


def _get_internal_nameservers() -> List[str]:
    return [
        str(HOSTS.resolve_domain(nameserver).ips[0])
        for nameserver in settings.DNS_SLAVE_SERVERS.keys()
    ]


def get_internal_resolver() -> DNSResolver:
    return DNSResolver(_get_internal_nameservers())


def get_google_resolver() -> DNSResolver:
    return DNSResolver(GOOGLE_DNS)


async def resolve_authoritative_ns_record(domain: str) -> List[str] | None:
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


async def get_ns_records(domain: str, ns_ip: str):
    ns_resolver = aiodns.DNSResolver(timeout=2)
    ns_resolver.nameservers = [ns_ip]
    result = await ns_resolver.query(domain, "NS")
    return sorted(str(r.host).rstrip(".") for r in result)


async def get_ns_records_from_public_ns(domain: str):
    tasks = [
        get_ns_records(domain, ns_ip=nameserver["ip"]) for nameserver in PUBLIC_DNS
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    ns_dict = {}
    for nameserver, result in zip(PUBLIC_DNS, results):
        ns_dict[nameserver["name"]] = result

    return ns_dict
