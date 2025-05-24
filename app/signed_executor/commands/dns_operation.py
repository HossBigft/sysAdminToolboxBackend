from __future__ import annotations
from app.signed_executor.commands.signed_operation import SignedOperation


class DNSOperation(SignedOperation):
    """Commands for NS (nameserver) operations."""

    def __init__(self, operation: str):
        super().__init__("DNS", operation)

    @classmethod
    def remove_zone(cls) -> DNSOperation:
        return cls("REMOVE_ZONE")

    @classmethod
    def get_zone_master(cls) -> DNSOperation:
        return cls("GET_ZONE_MASTER")
