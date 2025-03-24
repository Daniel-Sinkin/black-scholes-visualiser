"""Containts the constants."""

from dataclasses import dataclass, field
import datetime as dt
from typing import TypeAlias
import uuid


ORDER_ID: TypeAlias = str
POSITION_ID: TypeAlias = str
DEAL_ID: TypeAlias = str
USER_ID: TypeAlias = str


def _uuid4_str() -> str:
    return str(uuid.uuid4())


@dataclass
class Order:
    """Order Class"""

    owner_id: str
    is_buy: bool
    price: int
    volume: int
    comment: str
    order_id: ORDER_ID = field(default_factory=_uuid4_str)
    timestamp: dt.datetime = field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc)
    )


@dataclass
class Deal:
    """Deal Class"""

    volume: int
    price: int
    order_id_client: ORDER_ID
    order_id_market: ORDER_ID
    comment: str
    deal_id: DEAL_ID = field(default_factory=_uuid4_str)
    timestamp: dt.datetime = field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc)
    )
