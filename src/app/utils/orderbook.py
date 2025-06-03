from __future__ import annotations

import heapq
from typing import TYPE_CHECKING
from uuid import UUID

from src.app import models, schemas

if TYPE_CHECKING:
    from src.core.uow import UnitOfWork


class OrderBook:
    def __init__(self, instrument_id: UUID):
        self.instrument_id = instrument_id
        self.bids: list[tuple[int, float, schemas.orders.Read]] = []
        self.asks: list[tuple[int, float, schemas.orders.Read]] = []

    async def load_from_db(self, uow: UnitOfWork):
        active_orders = await uow.order_service.find_active_limit_orders(uow, self.instrument_id)

        buy_orders = []
        sell_orders = []

        # O(n)
        for order in active_orders:
            timestamp = order.created_at.timestamp()
            if order.direction == models.order.Direction.BUY:
                buy_orders.append((-order.price, timestamp, order))  # type: ignore[valid-type]
            else:
                sell_orders.append((order.price, timestamp, order))

        # O(n)
        heapq.heapify(buy_orders)
        heapq.heapify(sell_orders)

        self.bids = buy_orders
        self.asks = sell_orders

    def _add_order(self, order: schemas.orders.Read):
        if order.price is None:
            return

        timestamp = order.created_at.timestamp()
        if order.direction == models.order.Direction.BUY:
            heapq.heappush(self.bids, (-order.price, timestamp, order))
        else:
            heapq.heappush(self.asks, (order.price, timestamp, order))

    @staticmethod
    def _update_order_in_heap(heap, updated_order: schemas.orders.Read):
        for i, (_, _, order) in enumerate(heap):
            if order.id == updated_order.id:
                heap[i] = (heap[i][0], heap[i][1], updated_order)
                heapq.heapify(heap)
                break

    def _update_order_in_place(self, updated_order: schemas.orders.Read):
        if updated_order.direction == models.order.Direction.BUY:
            for _, _, order in self.bids:
                if order.id == updated_order.id:
                    order.filled = updated_order.filled
                    order.status = updated_order.status
                    order.locked_money_amount = updated_order.locked_money_amount
                    return
        else:
            for _, _, order in self.asks:
                if order.id == updated_order.id:
                    order.filled = updated_order.filled
                    order.status = updated_order.status
                    order.locked_instrument_amount = updated_order.locked_instrument_amount
                    return

    @staticmethod
    def _remove_order_from_heap(heap, order_id: UUID) -> None:
        for i, (_, _, order) in enumerate(heap):
            if order.id == order_id:
                heap.pop(i)
                heapq.heapify(heap)
                return

    @staticmethod
    def get_execution_price(
        sell_order: schemas.orders.Read, buy_order: schemas.orders.Read
    ) -> int:
        maker_order = sell_order if sell_order.created_at < buy_order.created_at else buy_order
        if maker_order.price is None:
            raise ValueError("Maker order price cannot be None")

        return maker_order.price

    async def execute_trade(
        self,
        uow: UnitOfWork,
        buy_order: schemas.orders.Read,
        sell_order: schemas.orders.Read,
        quantity: int,
    ) -> None:
        # maker price
        execution_price = self.get_execution_price(buy_order, sell_order)
        print(f"weaver qty start {quantity}")

        await uow.transaction_service.create(
            uow,
            schemas.transactions.Create(
                instrument_id=self.instrument_id,
                amount=quantity,
                price=execution_price,
            ),
        )

        rub_instrument = await uow.instrument_service.read_by_ticker(uow, "RUB")

        await uow.balance_service.transfer(
            uow,
            from_user_id=buy_order.user_id,
            to_user_id=sell_order.user_id,
            instrument_id=rub_instrument.id,
            amount=quantity * execution_price,
        )
        await uow.balance_service.transfer(
            uow,
            from_user_id=sell_order.user_id,
            to_user_id=buy_order.user_id,
            instrument_id=self.instrument_id,
            amount=quantity,
        )

        print(f"WEAVER buy order {buy_order}")
        print(f"WEAVER sell order {sell_order}")

        print(f"WEAVER quantity {quantity}")
        print(f"WEAVER execution_price {execution_price}")

        for order in [buy_order, sell_order]:
            if order.order_type == models.order.OrderType.LIMIT:
                updated_filled = (order.filled or 0) + quantity
                updated_status = (
                    models.order.OrderStatus.EXECUTED
                    if updated_filled == order.qty
                    else models.order.OrderStatus.PARTIALLY_EXECUTED
                )

                if order.direction == models.order.Direction.BUY:  # limit buy order
                    updated_locked_money_amount = (
                        order.locked_money_amount or 0
                    ) - quantity * execution_price
                    buy_order_update = schemas.orders.Update(
                        filled=updated_filled,
                        status=updated_status,
                        locked_money_amount=updated_locked_money_amount,
                    )
                    updated_buy_order = await uow.order_service.update_by_id(
                        uow, order.id, buy_order_update
                    )
                    if updated_buy_order.status == models.order.OrderStatus.EXECUTED:
                        self._remove_order_from_heap(self.bids, updated_buy_order.id)
                    else:
                        self._update_order_in_place(updated_buy_order)
                else:  # limit sell order
                    updated_locked_instrument_amount = (
                        order.locked_instrument_amount or 0
                    ) - quantity
                    sell_order_update = schemas.orders.Update(
                        filled=updated_filled,
                        status=updated_status,
                        locked_instrument_amount=updated_locked_instrument_amount,
                    )
                    updated_sell_order = await uow.order_service.update_by_id(
                        uow, order.id, sell_order_update
                    )
                    if updated_sell_order.status == models.order.OrderStatus.EXECUTED:
                        self._remove_order_from_heap(self.asks, updated_sell_order.id)
                    else:
                        self._update_order_in_place(updated_sell_order)
