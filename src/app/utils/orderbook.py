from __future__ import annotations

import heapq
from typing import TYPE_CHECKING
from uuid import UUID

from src import core
from src.app import models, schemas

if TYPE_CHECKING:
    from src.core.uow import UnitOfWork

type OrderHeap = list[schemas.orders.Read]


class OrderBook:
    def __init__(self, instrument_id: UUID):
        self.instrument_id = instrument_id
        self.bids: OrderHeap = []
        self.asks: OrderHeap = []

    async def load_from_db(
        self, uow: UnitOfWork, pagination: core.schemas.PaginationParams | None = None
    ):
        active_orders = await uow.order_service.find_active_limit_orders(
            uow, self.instrument_id, pagination
        )

        buy_orders, sell_orders = [], []

        # O(n)
        for order in active_orders:
            if order.direction == models.order.Direction.BUY:
                buy_orders.append(order)
            else:
                sell_orders.append(order)

        # O(n)
        heapq.heapify(buy_orders)
        heapq.heapify(sell_orders)

        self.bids = buy_orders
        self.asks = sell_orders

    @staticmethod
    def _update_heap_best_order(heap: OrderHeap, updated_order: schemas.orders.Read):
        print("!!! going to update")
        # O(1)
        if heap and (best_order := heap[0]).id == updated_order.id:
            best_order.filled = updated_order.filled
            best_order.status = updated_order.status

            if best_order.direction == models.order.Direction.BUY:
                best_order.locked_money_amount = updated_order.locked_money_amount
            else:
                best_order.locked_instrument_amount = updated_order.locked_instrument_amount

    @staticmethod
    def _remove_heap_best_order(heap: OrderHeap, order_id: UUID):
        # O(log(n))
        if heap and heap[0].id == order_id:
            heapq.heappop(heap)

    @staticmethod
    def get_execution_price(
        sell_order: schemas.orders.Read, buy_order: schemas.orders.Read
    ) -> int:
        maker_order = (
            sell_order
            if sell_order.created_at < buy_order.created_at
            or (
                sell_order.price and not buy_order.price
            )  # if orders were created at the same time (happens in tests)
            else buy_order
        )
        if maker_order.price is None:
            raise ValueError("Maker order price cannot be None")

        return maker_order.price

    async def execute_trade(
        self,
        uow: UnitOfWork,
        buy_order: schemas.orders.Read,
        sell_order: schemas.orders.Read,
        quantity: int,
    ) -> tuple[schemas.orders.Read | None, schemas.orders.Read | None]:
        # maker price
        execution_price = self.get_execution_price(buy_order, sell_order)

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
        await uow.transaction_service.create(
            uow,
            schemas.transactions.Create(
                instrument_id=self.instrument_id,
                amount=quantity,
                price=execution_price,
            ),
        )

        print(f"WEAVER buy order {buy_order}")
        print(f"WEAVER sell order {sell_order}")

        print(f"WEAVER quantity {quantity}")
        print(f"WEAVER execution_price {execution_price}")

        updated_buy_order, updated_sell_order = None, None
        for order in [buy_order, sell_order]:
            print(f"!!! going for order in {order}")
            if order.order_type == models.order.OrderType.LIMIT:
                updated_filled = (order.filled or 0) + quantity
                print(f"!!! updated_filled {updated_filled}")
                updated_status = (
                    models.order.OrderStatus.EXECUTED
                    if updated_filled == order.qty
                    else models.order.OrderStatus.PARTIALLY_EXECUTED
                )
                print(f"!!! updated_status {updated_status}")
                print(f"!!! order direction {order.direction}")
                if order.direction == models.order.Direction.BUY:  # LIMIT BUY order
                    updated_locked_money_amount = (order.locked_money_amount or 0) - quantity * (
                        order.price or 0
                    )

                    print(f"!!! updated_locked_money_amount {updated_locked_money_amount}")

                    buy_order_update = schemas.orders.Update(
                        filled=updated_filled,
                        status=updated_status,
                        locked_money_amount=updated_locked_money_amount,
                    )
                    print(f"!!! buy_order_update {buy_order_update}")
                    updated_buy_order = await uow.order_service.update_by_id(
                        uow, order.id, buy_order_update
                    )
                    print(f"!!! updated_buy_order {updated_buy_order}")
                    if updated_buy_order.status == models.order.OrderStatus.EXECUTED:
                        self._remove_heap_best_order(self.bids, updated_buy_order.id)
                    else:
                        self._update_heap_best_order(self.bids, updated_buy_order)
                else:  # LIMIT SELL order
                    updated_locked_instrument_amount = (
                        order.locked_instrument_amount or 0
                    ) - quantity
                    print(
                        f"!!! updated_locked_instrument_amount {updated_locked_instrument_amount}"
                    )
                    sell_order_update = schemas.orders.Update(
                        filled=updated_filled,
                        status=updated_status,
                        locked_instrument_amount=updated_locked_instrument_amount,
                    )
                    print(f"!!! sell_order_update {sell_order_update}")
                    updated_sell_order = await uow.order_service.update_by_id(
                        uow, order.id, sell_order_update
                    )
                    print(f"!!! updated_sell_order {updated_sell_order}")
                    if updated_sell_order.status == models.order.OrderStatus.EXECUTED:
                        self._remove_heap_best_order(self.asks, updated_sell_order.id)
                    else:
                        self._update_heap_best_order(self.asks, updated_sell_order)

        return (updated_buy_order, updated_sell_order)
