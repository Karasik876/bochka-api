from uuid import UUID

from sqlalchemy import select

from src import core
from src.app import models


class Balances(core.repositories.sqlalchemy.BaseCRUD[models.Balance]):
    def __init__(self):
        super().__init__(models.Balance)

    async def get_user_balances(self, uow: core.uow.UnitOfWork, user_id: UUID) -> dict[str, int]:
        try:
            session = uow.postgres_session

            instruments_query = select(models.Instrument.ticker)
            all_instruments = await session.scalars(instruments_query)
            all_instruments = set(all_instruments.all())

            balances_query = (
                select(models.Balance)
                .where(models.Balance.user_id == user_id)
                .where(models.Balance.deleted_at.is_(None))
            )

            user_balances = await session.scalars(balances_query)
            user_balances_dict = {balance.ticker: balance.amount for balance in user_balances}

            result = {}
            for ticker in all_instruments:
                result[ticker] = user_balances_dict.get(ticker, 0)

            return result
        except Exception as e:
            raise core.repositories.exceptions.DatabaseError(
                self.__class__.__name__,
                str(e),
            ) from e
