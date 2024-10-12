from dns import resolver, reversename, rdatatype


class RecordNotFoundError(Exception):
    def __init__(self, message):
        super().__init__(message)


def resolve_record(record: str, type: str, dns_list="hoster"):
    custom_resolver = resolver.Resolver()
    match dns_list:
        case "hoster":
            custom_resolver.nameservers = [
                "IP_PLACEHOLDER",
                "IP_PLACEHOLDER",
                "IP_PLACEHOLDER"
            ]
        case "free":
            custom_resolver.nameservers = ["IP_PLACEHOLDER", "IP_PLACEHOLDER"]
    try:
        match type:
            case "A":
                return [
                    ipval.to_text() for ipval in custom_resolver.resolve(record, type)
                ]
            case "PTR":
                addr_record = reversename.from_address(record)
                return str(custom_resolver.resolve(addr_record, type)[0])
            case "MX":
                return "".join(
                    [ipval.to_text() for ipval in custom_resolver.resolve(record, "MX")]
                ).split(" ")[1]
            case _:
                raise rdatatype.UnknownRdatatype
    except (resolver.NoAnswer, resolver.NXDOMAIN, resolver.NoNameservers) as exc:
        raise RecordNotFoundError(f"{type} record not found for {record}") from exc
