from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import Row, Uuid, select
from sqlalchemy.exc import OperationalError

from src import core
from src.app import models
from src.core.utils.decorators import retry_on_serialization

if TYPE_CHECKING:
    from src.core.uow import UnitOfWork


class Instruments(core.repositories.sqlalchemy.BaseCRUD[models.Instrument]):
    def __init__(self):
        super().__init__(models.Instrument)

    @retry_on_serialization()
    async def get_all_instruments(self, uow: UnitOfWork) -> Sequence[Row[tuple[Uuid, str]]]:
        try:
            session = uow.postgres_session

            instruments_query = select(models.Instrument.id, models.Instrument.ticker).where(
                models.Instrument.deleted_at.is_(None)
            )
            instruments = await session.execute(instruments_query)

            return instruments.all()
        except OperationalError:
            uow.postgres_session.expunge_all()
            raise

    @retry_on_serialization()
    async def read_by_ticker(
        self, uow: UnitOfWork, ticker: str, *, include_deleted: bool = False
    ) -> models.Instrument | None:
        try:
            query = select(models.Instrument).filter_by(ticker=ticker)

            if not include_deleted:
                query = query.where(models.Instrument.deleted_at.is_(None))

            return await uow.postgres_session.scalar(query)
        except OperationalError:
            uow.postgres_session.expunge_all()
            raise
