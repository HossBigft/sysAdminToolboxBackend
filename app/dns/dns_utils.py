from dns import resolver, reversename, rdatatype
from tldextract import extract

from app.core.DomainMapper import HOSTS
from app.core.config import settings

GOOGLE_DNS = ["8.8.8.8", "8.8.4.4"]


def resolve_record(record: str, type: str, dns_list="internal"):
    custom_resolver = resolver.Resolver()
    match dns_list:
        case "internal":
            custom_resolver.nameservers = [
                str(HOSTS.resolve_domain(nameserver).ips[0])
                for nameserver in list(settings.DNS_SLAVE_SERVERS.keys())
            ]
        case _:
            custom_resolver.nameservers = GOOGLE_DNS
    try:
        match type:
            case "A":
                return [
                    ipval.to_text() for ipval in custom_resolver.resolve(record, type)
                ]
            case "PTR":
                addr_record = reversename.from_address(record)
                return [
                    ipval.to_text()
                    for ipval in custom_resolver.resolve(addr_record, type)
                ]
            case "MX":
                return [
                    ipval.to_text().split(" ")[1]
                    for ipval in custom_resolver.resolve(record, "MX")
                ]
            case "NS":
                custom_resolver.nameservers = GOOGLE_DNS
                ns_records = [
                    str(record) for record in custom_resolver.resolve(record, "NS")
                ]
                ns_records.sort()
                return ns_records
            case "NS_AUTHORITATIVE":
                custom_resolver.nameservers = GOOGLE_DNS
                top_level_domain = extract(record).registered_domain
                soa_record = custom_resolver.resolve(top_level_domain, "SOA")[0].mname  # type: ignore
                primary_ns = str(soa_record).rstrip(".")
                primary_ns_ip = str(custom_resolver.resolve(primary_ns, "A")[0])
                custom_resolver.nameservers = [primary_ns_ip]

                ns_records = [
                    str(record) for record in custom_resolver.resolve(record, "NS")
                ]
                ns_records.sort()
                return ns_records
            case _:
                raise rdatatype.UnknownRdatatype
    except (resolver.NoAnswer, resolver.NXDOMAIN, resolver.NoNameservers):
        return None
