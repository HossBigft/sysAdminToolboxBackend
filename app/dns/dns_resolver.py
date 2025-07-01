import aiodns

from typing import List


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
