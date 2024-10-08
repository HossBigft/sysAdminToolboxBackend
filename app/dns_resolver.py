from dns import resolver, reversename
from typing import List


class RecordNotFoundError(Exception):
    def __init__(self, message):
        super().__init__(message)


def resolve_a_record(domain: str) -> List[str]:
    try:
        return [ipval.to_text() for ipval in resolver.resolve(domain, "A")]
    except (resolver.NoAnswer, resolver.NXDOMAIN, resolver.NoNameservers) as exc:
        raise RecordNotFoundError(f"A record not found for {domain}") from exc


def resolve_ptr_record(ip: str) -> str:
    try:
        addr_record = reversename.from_address(ip)
        return str(resolver.resolve(addr_record, "PTR")[0])
    except (resolver.NoAnswer, resolver.NXDOMAIN) as exc:
        raise RecordNotFoundError(f"PTR record not found for {ip}") from exc


def resolve_mx_record(domain) -> List[str]:
    try:
        return "".join(
            [ipval.to_text() for ipval in resolver.resolve(domain, "MX")]
        ).split(" ")[1]
    except (resolver.NoAnswer, resolver.NXDOMAIN, resolver.NoNameservers) as exc:
        raise RecordNotFoundError(f"MX record not found for {domain}") from exc
