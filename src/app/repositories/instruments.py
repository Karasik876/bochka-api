from collections.abc import Sequence

from sqlalchemy import select

from src import core
from src.app import models


class Instruments(core.repositories.sqlalchemy.BaseCRUD[models.Instrument]):
    def __init__(self):
        super().__init__(models.Instrument)

    @staticmethod
    async def get_all_tickers(uow: core.UnitOfWork) -> Sequence[str]:
        session = uow.postgres_session

        instruments_query = select(models.Instrument.ticker)
        instruments = await session.scalars(instruments_query)

        return instruments.all()
