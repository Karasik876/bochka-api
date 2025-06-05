from typing import cast
from uuid import UUID

from src import core
from src.app import models, repositories, schemas, services

from . import exceptions


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

        self.order_handlers = {
            ("MARKET", "BUY"): self._handle_market_buy,
            ("MARKET", "SELL"): self._handle_market_sell,
            ("LIMIT", "BUY"): self._handle_limit_buy,
            ("LIMIT", "SELL"): self._handle_limit_sell,
        }

        self.instruments_service = services.Instruments()
        self.balances_service = services.Balances()
        self.transactions_service = services.Transactions()

    async def _transfer_locked_amount_to_balance(
        self,
        uow: core.UnitOfWork,
        from_order_id: UUID,
        to_user_id: UUID,
        instrument_id: UUID,
        amount: int,
    ) -> None:
        order = await self.read_by_id(uow, from_order_id)

        to_balance = await self.balances_service.get_or_create_user_balance(
            uow, to_user_id, instrument_id
        )

        new_locked_amount = order.locked_amount - amount

        new_balance_amount = to_balance.amount + amount

        await self.update_by_id(
            uow,
            order.id,
            schemas.orders.Update(locked_amount=new_locked_amount),
        )
        await self.balances_service.update_by_id(
            uow,
            {"user_id": to_user_id, "instrument_id": instrument_id},
            schemas.balance.Update(amount=new_balance_amount),
        )

    async def _return_locked_amount(self, uow: core.UnitOfWork, order_id: UUID) -> None:
        order = await self.read_by_id(uow, order_id)
        rub_instrument = await self.instruments_service.read_by_ticker(uow, "RUB")

        if order.locked_amount > 0:
            await self._transfer_locked_amount_to_balance(
                uow,
                from_order_id=order.id,
                to_user_id=order.user_id,
                instrument_id=rub_instrument.id
                if order.direction == "BUY"
                else order.instrument.id,
                amount=order.locked_amount,
            )

    async def _create_transaction(
        self,
        uow: core.UnitOfWork,
        buy_order_id: UUID,
        sell_order_id: UUID,
        instrument_id: UUID,
        qty: int,
        price: int,
    ) -> None:
        await self.transactions_service.create(
            uow,
            schemas.transactions.Create(
                buy_order_id=buy_order_id,
                sell_order_id=sell_order_id,
                instrument_id=instrument_id,
                qty=qty,
                price=price,
            ),
        )

    async def _update_balances(
        self,
        uow: core.UnitOfWork,
        buy_order_id: UUID,
        sell_order_id: UUID,
        buyer_id: UUID,
        seller_id: UUID,
        instrument_id: UUID,
        qty: int,
        price: int,
    ) -> None:
        # Перевод инструмента покупателю
        await self._transfer_locked_amount_to_balance(
            uow,
            from_order_id=sell_order_id,
            to_user_id=buyer_id,
            instrument_id=instrument_id,
            amount=qty,
        )

        rub_instrument = await self.instruments_service.read_by_ticker(uow, "RUB")

        # Перевод рублей продавцу
        await self._transfer_locked_amount_to_balance(
            uow,
            from_order_id=buy_order_id,
            to_user_id=seller_id,
            instrument_id=rub_instrument.id,
            amount=price,
        )

    async def _execute_trade(
        self,
        uow: core.UnitOfWork,
        buy_order: schemas.orders.Read,
        sell_order: schemas.orders.Read,
        executed_qty: int,
    ) -> None:
        price = cast(int, sell_order.price) if sell_order.price else cast(int, buy_order.price)
        price *= executed_qty

        await self._update_balances(
            uow,
            buy_order_id=buy_order.id,
            sell_order_id=sell_order.id,
            buyer_id=buy_order.user_id,
            seller_id=sell_order.user_id,
            instrument_id=buy_order.instrument.id,
            qty=executed_qty,
            price=price,
        )

        await self._create_transaction(
            uow,
            buy_order_id=buy_order.id,
            sell_order_id=sell_order.id,
            instrument_id=buy_order.instrument.id,
            qty=executed_qty,
            price=price,
        )

        new_filled_buy = buy_order.filled + executed_qty
        buy_status = (
            models.OrderStatus.EXECUTED
            if new_filled_buy == buy_order.qty
            else models.OrderStatus.PARTIALLY_EXECUTED
        )

        await self.update_by_id(
            uow,
            buy_order.id,
            schemas.orders.Update(
                filled=new_filled_buy,
                status=buy_status,
            ),
        )

        if buy_status == models.OrderStatus.EXECUTED:
            await self._return_locked_amount(uow, buy_order.id)

        # Обновление ордера на продажу
        new_filled_sell = sell_order.filled + executed_qty
        sell_status = (
            models.OrderStatus.EXECUTED
            if new_filled_sell == sell_order.qty
            else models.OrderStatus.PARTIALLY_EXECUTED
        )

        if sell_status == models.OrderStatus.EXECUTED:
            await self._return_locked_amount(uow, sell_order.id)

        await self.update_by_id(
            uow, sell_order.id, schemas.orders.Update(filled=new_filled_sell, status=sell_status)
        )

    async def _find_best_order(
        self, uow: core.UnitOfWork, instrument_id: UUID, order_direction: models.OrderDirection
    ) -> schemas.orders.Read | None:
        orders = await self.read_many(
            uow,
            schemas.orders.Filters(
                direction=order_direction,
                instrument_id=instrument_id,
                status=[models.OrderStatus.NEW, models.OrderStatus.PARTIALLY_EXECUTED],
            ),
            schemas.orders.SortParams(
                sort_by=schemas.orders.SortFields.PRICE,
                ascending=order_direction == models.OrderDirection.BUY,
            ),
            core.schemas.PaginationParams(limit=1),
        )

        if not orders:
            return None

        return orders[0]

    async def reserve(
        self, uow: core.UnitOfWork, user_id: UUID, instrument_id: UUID, order_id: UUID, amount: int
    ) -> None:
        balance = await self.balances_service.get_or_create_user_balance(
            uow, user_id, instrument_id
        )

        new_balance = balance.amount - amount

        if new_balance < 0:
            instrument = await self.instruments_service.read_by_id(uow, instrument_id)
            raise services.exceptions.InsufficientBalanceError(user_id, instrument.ticker)

        await self.balances_service.update_by_id(
            uow,
            {"user_id": user_id, "instrument_id": instrument_id},
            schemas.balance.Update(amount=new_balance),
        )

        await self.update_by_id(uow, order_id, schemas.orders.Update(locked_amount=amount))

    async def _handle_market_buy(self, uow: core.UnitOfWork, order: schemas.orders.Read) -> None:
        rub_instrument = await self.instruments_service.read_by_ticker(uow, "RUB")

        filled = order.filled
        while filled < order.qty:
            sell_order = await self._find_best_order(
                uow, order.instrument.id, models.OrderDirection.SELL
            )

            if not sell_order:
                raise exceptions.OrderRejectedError(order.id, order.qty, filled)

            executed_qty = min(sell_order.qty - sell_order.filled, order.qty - order.filled)

            locked_money_amount = cast(int, sell_order.price) * executed_qty
            await self.reserve(
                uow, order.user_id, rub_instrument.id, order.id, locked_money_amount
            )

            await self._execute_trade(uow, order, sell_order, executed_qty)
            filled += executed_qty

    async def _handle_market_sell(self, uow: core.UnitOfWork, order: schemas.orders.Read) -> None:
        await self.reserve(uow, order.user_id, order.instrument.id, order.id, order.qty)

        filled = order.filled
        while filled < order.qty:
            buy_order = await self._find_best_order(
                uow, order.instrument.id, models.OrderDirection.BUY
            )
            if not buy_order:
                raise exceptions.OrderRejectedError(order.id, order.qty, filled)

            executed_qty = min(buy_order.qty - buy_order.filled, order.qty - order.filled)

            await self._execute_trade(uow, buy_order, order, executed_qty)
            filled += executed_qty

    async def _handle_limit_buy(self, uow: core.UnitOfWork, order: schemas.orders.Read) -> None:
        rub_instrument = await self.instruments_service.read_by_ticker(uow, "RUB")
        locked_money_amount = cast(int, order.price) * order.qty

        await self.reserve(uow, order.user_id, rub_instrument.id, order.id, locked_money_amount)

        filled = order.filled
        while filled < order.qty:
            sell_order = await self._find_best_order(
                uow, order.instrument.id, models.OrderDirection.SELL
            )
            if not sell_order:
                break

            executed_qty = min(sell_order.qty - sell_order.filled, order.qty - order.filled)

            await self._execute_trade(uow, order, sell_order, executed_qty)
            filled += executed_qty

    async def _handle_limit_sell(self, uow: core.UnitOfWork, order: schemas.orders.Read) -> None:
        await self.reserve(uow, order.user_id, order.instrument.id, order.id, order.qty)

        filled = order.filled
        while filled < order.qty:
            buy_order = await self._find_best_order(
                uow, order.instrument.id, models.OrderDirection.BUY
            )
            if not buy_order:
                break

            executed_qty = min(buy_order.qty - buy_order.filled, order.qty - order.filled)

            await self._execute_trade(uow, buy_order, order, executed_qty)
            filled += executed_qty

    async def create(
        self,
        uow: core.UnitOfWork,
        order_data: schemas.orders.Create,
        additional_data: dict,
    ) -> schemas.orders.Read:
        instrument = await self.instruments_service.read_by_ticker(uow, order_data.ticker)
        additional_data["instrument_id"] = instrument.id

        order = await super().create(uow, order_data, additional_data=additional_data)

        await self.order_handlers[order.order_type, order.direction](uow, order)

        return order

    async def cancel_order(self, uow: core.UnitOfWork, order_id: UUID):
        order = await self.read_by_id(uow, order_id)

        await self._return_locked_amount(uow, order)

        await self.update_by_id(
            uow, order_id, schemas.orders.Update(status=models.order.OrderStatus.CANCELLED)
        )
