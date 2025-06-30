import aiodns
import asyncio
from dns import resolver, reversename
from tldextract import extract

from typing import List
from collections import defaultdict
from app.core.DomainMapper import HOSTS
from app.core.config import settings

GOOGLE_DNS = ["8.8.8.8", "8.8.4.4"]

PUBLIC_DNS = [
    "208.67.222.220",
    "9.9.9.9",
    "216.146.35.35",
    "204.12.225.227",
    "207.177.68.4",
    "156.154.70.64",
    "208.91.112.53",
    "195.46.39.39",
    "5.11.11.11",
    "87.213.100.113",
    "83.145.86.7",
    "212.230.255.1",
    "83.137.41.9",
    "194.145.240.6",
    "195.243.214.4",
    "200.52.177.186",
    "200.248.178.54",
    "211.25.206.147",
    "1.1.1.1",
    "61.8.0.113",
    "122.56.107.86",
    "139.59.219.245",
    "164.124.101.2",
    "114.114.115.115",
    "31.7.37.37",
    "115.178.96.2",
    "209.150.154.1",
    "194.125.133.10",
    "103.80.1.2",
]


class DNSResolver:
    def __init__(self, nameservers: List[str]):
        self.resolver = aiodns.DNSResolver(timeout=2)
        self.resolver.nameservers = nameservers

    async def resolve_a(self, domain: str) -> List[str] | None:
        try:
            result = await self.resolver.query(domain, "A")
            return [str(r.host) for r in result]
        except (aiodns.error.DNSError, Exception):
            return None

    async def resolve_ptr(self, domain: str) -> List[str] | None:
        try:
            addr_record = reversename.from_address(domain)
            return [ip.to_text() for ip in self.resolver.query(addr_record, "PTR")]
        except (resolver.NoAnswer, resolver.NXDOMAIN, resolver.NoNameservers):
            return None

    async def resolve_mx(self, domain: str) -> List[str] | None:
        try:
            return [
                mx.to_text().split(" ", 1)[1]
                for mx in self.resolver.query(domain, "MX")
            ]
        except (resolver.NoAnswer, resolver.NXDOMAIN, resolver.NoNameservers):
            return None

    async def resolve_ns(self, domain: str) -> List[str] | None:
        try:
            ns_records = [
                str(ns_record) for ns_record in self.resolver.query(domain, "NS")
            ]
            return sorted(ns_records)
        except (resolver.NoAnswer, resolver.NXDOMAIN, resolver.NoNameservers):
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


def resolve_authoritative_ns_record(domain: str) -> List[str] | None:
    try:
        google_resolver = resolver.Resolver()
        google_resolver.nameservers = GOOGLE_DNS

        top_level_domain = extract(domain).registered_domain
        soa_record = google_resolver.query(top_level_domain, "SOA")[0].mname
        primary_ns = str(soa_record).rstrip(".")
        primary_ns_ip = str(google_resolver.query(primary_ns, "A")[0])

        auth_resolver = resolver.Resolver()
        auth_resolver.nameservers = [primary_ns_ip]

        ns_records = [
            str(ns_record) for ns_record in auth_resolver.query(domain, "NS")
        ]
        return sorted(ns_records)
    except (resolver.NoAnswer, resolver.NXDOMAIN, resolver.NoNameservers):
        return None


async def get_ns_records(domain: str, dns_server: str):

    resolver = aiodns.DNSResolver(timeout=2)
    try:
        # Set custom nameserver
        resolver.nameservers = [dns_server]
        result = await resolver.query(domain, 'NS')
        return dns_server, sorted(r.host.rstrip('.') for r in result)
    except Exception as e:
        return dns_server, f"Error: {e}"


ALL_DNS = GOOGLE_DNS + PUBLIC_DNS

async def collect_all_ns(domain: str):
    tasks = [get_ns_records(domain, dns_ip) for dns_ip in ALL_DNS]
    results = await asyncio.gather(*tasks)
    return dict(results)
