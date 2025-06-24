from dns import resolver, reversename
from tldextract import extract
from typing import List

from app.core.DomainMapper import HOSTS
from app.core.config import settings

GOOGLE_DNS = ["8.8.8.8", "8.8.4.4"]


class DNSResolver:
    def __init__(self, nameservers: List[str]):
        self.resolver = resolver.Resolver()
        self.resolver.nameservers = nameservers

    def resolve_a(self, domain: str) -> List[str] | None:
        try:
            return [ip.to_text() for ip in self.resolver.resolve(domain, "A")]
        except (resolver.NoAnswer, resolver.NXDOMAIN, resolver.NoNameservers):
            return None

    def resolve_ptr(self, domain: str) -> List[str] | None:
        try:
            addr_record = reversename.from_address(domain)
            return [ip.to_text() for ip in self.resolver.resolve(addr_record, "PTR")]
        except (resolver.NoAnswer, resolver.NXDOMAIN, resolver.NoNameservers):
            return None

    def resolve_mx(self, domain: str) -> List[str] | None:
        try:
            return [
                mx.to_text().split(" ", 1)[1]
                for mx in self.resolver.resolve(domain, "MX")
            ]
        except (resolver.NoAnswer, resolver.NXDOMAIN, resolver.NoNameservers):
            return None

    def resolve_ns(self, domain: str) -> List[str] | None:
        try:
            ns_records = [
                str(ns_record) for ns_record in self.resolver.resolve(domain, "NS")
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
        soa_record = google_resolver.resolve(top_level_domain, "SOA")[0].mname
        primary_ns = str(soa_record).rstrip(".")
        primary_ns_ip = str(google_resolver.resolve(primary_ns, "A")[0])

        auth_resolver = resolver.Resolver()
        auth_resolver.nameservers = [primary_ns_ip]

        ns_records = [
            str(ns_record) for ns_record in auth_resolver.resolve(domain, "NS")
        ]
        return sorted(ns_records)
    except (resolver.NoAnswer, resolver.NXDOMAIN, resolver.NoNameservers):
        return None
