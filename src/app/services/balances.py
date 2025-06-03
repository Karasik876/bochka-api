from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from src import core
from src.app import models, repositories, schemas, services

if TYPE_CHECKING:
    from src.core.uow import UnitOfWork


class Balances(
    core.services.BaseCRUD[
        schemas.balance.Create,
        schemas.balance.Read,
        schemas.balance.Update,
        schemas.balance.Filters,
        schemas.balance.SortParams,
        models.Balance,
    ],
):
    def __init__(self):
        self.repo = repositories.Balances()
        super().__init__(
            repo=self.repo,
            create_schema=schemas.balance.Create,
            read_schema=schemas.balance.Read,
            update_schema=schemas.balance.Update,
            filters_schema=schemas.balance.Filters,
        )

    async def transfer(
        self,
        uow: UnitOfWork,
        from_user_id: UUID,
        to_user_id: UUID,
        instrument_id: UUID,
        amount: int,
    ) -> None:
        from_balance = await uow.balance_service.get_or_create_user_balance(
            uow, from_user_id, instrument_id
        )

        if from_balance.amount < amount:
            instrument = await uow.instrument_service.read_by_id(uow, instrument_id)
            raise services.exceptions.InsufficientBalanceError(from_user_id, instrument.ticker)

        to_balance = await uow.balance_service.get_or_create_user_balance(
            uow, to_user_id, instrument_id
        )

        from_balance.amount -= amount
        to_balance.amount += amount

        await self.update_by_id(
            uow,
            {"user_id": from_user_id, "instrument_id": instrument_id},
            schemas.balance.Update(amount=from_balance.amount),
        )
        await self.update_by_id(
            uow,
            {"user_id": to_user_id, "instrument_id": instrument_id},
            schemas.balance.Update(amount=to_balance.amount),
        )

    async def get_or_create_user_balance(
        self, uow: UnitOfWork, user_id: UUID, instrument_id: UUID
    ) -> schemas.balance.Read:
        try:
            balance = await self.read_by_id(
                uow, {"user_id": user_id, "instrument_id": instrument_id}
            )
        except core.services.exceptions.EntityNotFoundError:
            balance = await self.create(
                uow,
                schemas.balance.Create(
                    user_id=user_id,
                    instrument_id=instrument_id,
                    amount=0,
                ),
            )

        return balance
