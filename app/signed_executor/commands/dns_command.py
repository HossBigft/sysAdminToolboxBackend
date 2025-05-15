from __future__ import annotations
from app.signed_executor.commands.signed_command import SignedCommand


class DNSCommand(SignedCommand):
    """Commands for NS (nameserver) operations."""

    def __init__(self, operation: str):
        super().__init__("DNS", operation)

    @classmethod
    def remove_zone(cls) -> DNSCommand:
        return cls("REMOVE_ZONE")

    @classmethod
    def get_zone_master(cls) -> DNSCommand:
        return cls("GET_ZONE_MASTER")
