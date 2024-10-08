from dns import resolver, reversename, rdatatype


class RecordNotFoundError(Exception):
    def __init__(self, message):
        super().__init__(message)


def resolve_record(record: str, type: str):
    try:
        match type:
            case "A":
                return [ipval.to_text() for ipval in resolver.resolve(record, type)]
            case "PTR":
                addr_record = reversename.from_address(record)
                return str(resolver.resolve(addr_record, type)[0])
            case "MX":
                return "".join(
                    [ipval.to_text() for ipval in resolver.resolve(record, "MX")]
                ).split(" ")[1]
            case _:
                raise rdatatype.UnknownRdatatype
    except (resolver.NoAnswer, resolver.NXDOMAIN, resolver.NoNameservers) as exc:
        raise RecordNotFoundError(f"{type} record not found for {record}") from exc
