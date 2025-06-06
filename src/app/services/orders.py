from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from src import core
from src.app import models, repositories, schemas, services, utils

if TYPE_CHECKING:
    from src.core.uow import UnitOfWork


class Orders(
    core.services.BaseCRUD[
        schemas.orders.Create,
        schemas.orders.Read,
        schemas.orders.Update,
        schemas.orders.Filters,
        schemas.orders.SortParams,
        models.Order,
    ]
):
    def __init__(self):
        self.repo = repositories.Orders()
        super().__init__(
            self.repo,
            create_schema=schemas.orders.Create,
            read_schema=schemas.orders.Read,
            update_schema=schemas.orders.Update,
            filters_schema=schemas.orders.Filters,
        )

    async def find_active_limit_orders(
        self,
        uow: UnitOfWork,
        instrument_id: UUID,
        pagination: core.schemas.PaginationParams | None = None,
    ) -> list[schemas.orders.Read]:
        buy_orders = await self.read_many(
            uow,
            filters=schemas.orders.Filters(
                instrument_id=instrument_id,
                order_type=models.order.OrderType.LIMIT,
                status=[models.order.OrderStatus.NEW, models.order.OrderStatus.PARTIALLY_EXECUTED],
                direction=models.order.Direction.BUY,
            ),
            pagination=pagination,
        )
        sell_orders = await self.read_many(
            uow,
            filters=schemas.orders.Filters(
                instrument_id=instrument_id,
                order_type=models.order.OrderType.LIMIT,
                status=[models.order.OrderStatus.NEW, models.order.OrderStatus.PARTIALLY_EXECUTED],
                direction=models.order.Direction.SELL,
            ),
            pagination=pagination,
        )
        buy_orders.extend(sell_orders)
        return buy_orders

    async def create(
        self,
        uow: UnitOfWork,
        create_schema: schemas.orders.Create,
        *,
        additional_data: dict[str, Any] | None = None,
    ) -> schemas.orders.Read:
        user_id = create_schema.user_id
        instrument_id = create_schema.instrument_id
        direction = create_schema.direction
        qty = create_schema.qty
        price = create_schema.price
        order_type = create_schema.order_type

        print("Starting weaver Order create")
        print(f"instrument_id: {instrument_id}")
        print(f"direction: {direction}")
        print(f"qty: {qty}")
        print(f"price: {price}")
        print(f"order_type: {order_type}")

        rub_instrument = await uow.instrument_service.read_by_ticker(uow, "RUB")

        rub_balance = await uow.balance_service.get_or_create_user_balance(
            uow, user_id, rub_instrument.id
        )

        instrument_balance = await uow.balance_service.get_or_create_user_balance(
            uow, user_id, instrument_id
        )

        if order_type == models.order.OrderType.LIMIT:
            filled = 0
            if direction == models.order.Direction.BUY:
                locked_money = await self.repo.sum_locked_money(uow, user_id)

                if price is None:
                    raise ValueError("Limit orders require price")

                required_money = qty * price
                available_money = rub_balance.amount - locked_money

                if available_money < required_money:
                    print(f"dazzle available_money {available_money}")
                    print(f"dazzle required_money {required_money}")
                    raise services.exceptions.InsufficientBalanceError(user_id, "RUB")

                locked_money_amount = required_money
                locked_instrument_amount = None

            else:  # SELL
                locked_instrument = await self.repo.sum_locked_instrument(
                    uow, user_id, instrument_id
                )

                available_instrument = instrument_balance.amount - locked_instrument

                if available_instrument < qty:
                    instrument = await uow.instrument_service.read_by_id(uow, instrument_id)
                    print(f"dazzle available_instrument {available_instrument}")
                    print(f"dazzle qty {qty}")
                    raise services.exceptions.InsufficientBalanceError(user_id, instrument.ticker)

                locked_money_amount = None
                locked_instrument_amount = qty

        else:  # MARKET ORDER
            locked_money_amount = None
            locked_instrument_amount = None
            filled = None

        additional_data = additional_data or {}
        additional_data.update({
            "locked_money_amount": locked_money_amount,
            "locked_instrument_amount": locked_instrument_amount,
            "filled": filled,
        })

        print(f"Weaver additional data: {additional_data}")

        order = await super().create(uow, create_schema, additional_data=additional_data)

        print(f"Weaver created ORDER: {order}")
        order_book_manager = utils.get_order_book_manager()

        if order_type == models.order.OrderType.MARKET:
            await self._execute_market_order(
                uow=uow,
                order_book_manager=order_book_manager,
                instrument_id=instrument_id,
                order=order,
            )

        return order

    @staticmethod
    async def _execute_market_order(
        uow: UnitOfWork,
        order_book_manager: utils.OrderBookManager,
        instrument_id: UUID,
        order: schemas.orders.Read,
    ) -> None:
        order_book = await order_book_manager.get_order_book(uow, instrument_id)

        remaining_qty = order.qty
        while remaining_qty > 0:
            if order.direction == models.order.Direction.BUY:
                best_ask_order = order_book.asks[0] if order_book.asks else None
                if not best_ask_order:
                    break

                if (available_qty := best_ask_order.qty - best_ask_order.filled) == 0:
                    break

                trade_qty = min(remaining_qty, available_qty)

                await order_book.execute_trade(uow, order, best_ask_order, trade_qty)

                remaining_qty -= trade_qty

            else:  # SELL
                best_bid_order = order_book.bids[0] if order_book.bids else None
                if not best_bid_order:
                    break

                if (available_qty := best_bid_order.qty - best_bid_order.filled) == 0:
                    break

                trade_qty = min(remaining_qty, available_qty)

                await order_book.execute_trade(uow, best_bid_order, order, trade_qty)

                remaining_qty -= trade_qty

        if remaining_qty != 0:
            order_book_manager.clear_order_book(instrument_id)
            raise services.exceptions.OrderRejectedError(order.id, order.qty, remaining_qty)
