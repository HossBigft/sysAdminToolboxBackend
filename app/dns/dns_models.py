from typing import List

from pydantic import (
    BaseModel
)
from app.schemas import IPv4Address


class ZoneMaster(BaseModel):
    host: str
    ip: IPv4Address


class ZoneMasterResponse(BaseModel):
    zone_name: str
    zone_masters: List[ZoneMaster]
