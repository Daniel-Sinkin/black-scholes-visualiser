"""Contains the Orderbook class."""

import datetime as dt
from collections import deque
from typing import cast

from sortedcontainers import SortedDict

from .constants import Deal, Order, ORDER_ID, DEAL_ID, USER_ID


class Orderbook:
    """The Orderbook class"""

    def __init__(self):
        self.bids = SortedDict(lambda x: -x)
        self.asks = SortedDict()

        self._long_num_ords = self.get_long_num_ords()
        self._short_num_ords = self.get_short_num_ords()

        self._short_volume = self.get_total_short_volume()
        self._long_volume = self.get_total_long_volume()

        self._deals: list[Deal] = []
        self._orders: list[Order] = []

        self._latest_order_dt: dt.datetime | None = None

        self._DEBUG_creation_time = dt.datetime.now(dt.timezone.utc)
        self._DEBUG_disable_cache: bool = True

    def validate(self) -> None:
        assert (
            self._short_volume == self.get_total_short_volume()
        ), "Volume mismatch for Short Orders!"
        assert (
            self._long_volume == self.get_total_long_volume()
        ), "Volume mismatch for Long Orders!"
        if len(self.asks) > 0 and len(self.bids) > 0:
            assert (
                self.get_min_ask_price() > self.get_max_bid_price()
            ), "ASKS and BIDS are mismatched!"

    def get_max_bid_price(self) -> int:
        return next(iter(self.bids))

    def get_min_ask_price(self) -> int:
        return next(iter(self.asks))

    def get_long_num_ords(self) -> int:
        return sum(len(ords) for ords in self.asks.values())

    def get_short_num_ords(self) -> int:
        return sum(len(ords) for ords in self.bids.values())

    def get_total_long_volume(self) -> int:
        return sum(sum((ord.volume for ord in ords)) for ords in self.asks.values())

    def get_total_short_volume(self) -> int:
        return sum(sum((ord.volume for ord in ords)) for ords in self.bids.values())

    def create_new_order(
        self,
        owner_id: USER_ID,
        is_buy: bool,
        price: int,
        volume: int,
        comment: str = "",
    ) -> Order:
        new_order = Order(
            owner_id=owner_id,
            is_buy=is_buy,
            price=price,
            volume=volume,
            comment=comment,
        )

        if not self._DEBUG_disable_cache:
            self._orders.append(new_order)
        return new_order

    def create_new_deal(
        self,
        volume: int,
        price: int,
        order_id_client: ORDER_ID,
        order_id_market: ORDER_ID,
        comment: str = "",
    ) -> Deal:
        new_deal = Deal(
            volume=volume,
            price=price,
            order_id_client=order_id_client,
            order_id_market=order_id_market,
            comment=comment,
        )
        if not self._DEBUG_disable_cache:
            self._deals.append(new_deal)
        return new_deal

    def submit_limit_order(
        self, owner_id: USER_ID, is_buy: bool, price: int, volume: int
    ) -> tuple[ORDER_ID | None, str | None]:
        if (
            is_buy
            and len(self.bids) > 0
            and price <= (max_bid_price := self.get_max_bid_price())
        ):
            return (
                None,
                f"Rejected order ask price '{price}', lower than {max_bid_price}.",
            )
        if (
            not is_buy
            and len(self.asks) > 0
            and price >= (min_buy_price := self.get_min_ask_price())
        ):
            return (
                None,
                f"Rejected order bid price '{price}', higher than {min_buy_price}.",
            )

        new_order = self.create_new_order(
            owner_id=owner_id, is_buy=is_buy, price=price, volume=volume
        )
        if is_buy:
            self._long_volume += volume
        else:
            self._short_volume += volume

        price_map = self.asks if is_buy else self.bids
        if price not in price_map:
            price_map[price] = deque([new_order])
        else:
            price_map[price].append(new_order)

        return new_order.order_id, None

    def submit_market_order(
        self, owner_id: USER_ID, is_buy: bool, volume: int
    ) -> tuple[DEAL_ID | None, str | None]:
        if not is_buy:
            return None, "Short Market Orders currently not supported!"

        if is_buy and (volume > self._short_volume):
            return None, f"{volume=}>{self._short_volume=}!"
        if not is_buy and (volume > self._long_volume):
            return None, f"{volume=}>{self._long_volume=}!"

        deal_ids: list[DEAL_ID] = []
        while True:
            price_level = self.get_max_bid_price()

            while len(self.bids[price_level]) > 0:
                order = cast(Order, self.bids[price_level][0])
                filled_volume = min(order.volume, volume)

                filling_order = self.create_new_order(
                    owner_id=owner_id,
                    is_buy=is_buy,
                    price=price_level,
                    volume=filled_volume,
                )

                new_deal = self.create_new_deal(
                    volume=filled_volume,
                    price=price_level,
                    order_id_market=order.order_id,
                    order_id_client=filling_order.order_id,
                )
                deal_ids.append(new_deal.deal_id)

                volume -= filled_volume
                if filled_volume < order.volume:
                    # Partial fill
                    self.bids[price_level][0].volume -= filled_volume
                    self._short_volume -= filled_volume
                else:
                    # Fully filled
                    filled_order = self.bids[price_level].popleft()
                    self._short_volume -= filled_order.volume

                if volume == 0:
                    return deal_ids, None
