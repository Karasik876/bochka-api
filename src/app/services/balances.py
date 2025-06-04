from uuid import UUID

from src import core
from src.app import models, repositories, schemas, services


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

        self.instrument_service = services.Instruments()

    async def reserve(self, uow: core.UnitOfWork, user_id: UUID, instrument_id: UUID, amount: int) -> None:
        balance = await self.get_or_create_user_balance(uow, user_id, instrument_id)
        balance.amount -= amount

        if balance.amount < 0:
            instrument = await self.instrument_service.read_by_id(uow, instrument_id)
            raise services.exceptions.InsufficientBalanceError(user_id, instrument.ticker)

        balance.locked_amount += amount

        await self.update_by_id(
            uow,
            {"user_id": user_id, "instrument_id": instrument_id},
            schemas.balance.Update(amount=balance.amount, locked_amount=balance.locked_amount),
        )

    async def transfer(
        self,
        uow: core.UnitOfWork,
        from_user_id: UUID,
        to_user_id: UUID,
        instrument_id: UUID,
        amount: int,
    ) -> None:
        from_balance = await self.get_or_create_user_balance(uow, from_user_id, instrument_id)

        to_balance = await self.get_or_create_user_balance(uow, to_user_id, instrument_id)

        from_balance.locked_amount -= amount
        to_balance.amount += amount

        await self.update_by_id(
            uow,
            {"user_id": from_user_id, "instrument_id": instrument_id},
            schemas.balance.Update(locked_amount=from_balance.locked_amount),
        )
        await self.update_by_id(
            uow,
            {"user_id": to_user_id, "instrument_id": instrument_id},
            schemas.balance.Update(amount=to_balance.amount),
        )

    async def get_or_create_user_balance(
        self, uow: core.UnitOfWork, user_id: UUID, instrument_id: UUID
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
