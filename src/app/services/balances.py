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
