from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from src.app import models
from src.core.repositories.sqlalchemy import BaseCRUD
from src.core.uow import UnitOfWork

pytestmark = pytest.mark.asyncio(loop_scope="session")


def make_serialization_error():
    class CustomError(Exception):
        def __init__(self, pgcode):
            super().__init__()
            self.pgcode = pgcode

    orig = CustomError("40001")
    return OperationalError("serialization error", params=None, orig=orig)


async def test_create_retries_on_serialization_error(db_session: AsyncSession):
    instruments_repo = BaseCRUD(models.Instrument)

    attempts = [
        make_serialization_error(),
        make_serialization_error(),
        None,  # success on 3rd attempt
    ]

    flush_mock = AsyncMock(spec=AsyncSession.flush, side_effect=attempts)
    refresh_mock = (
        AsyncMock()
    )  # Fix to "Instance '<Instrument at 0x1f301df9550>' is not persistent within this Session"

    async with UnitOfWork(use_postgres=False) as uow:
        uow._postgres_session = db_session  # noqa: SLF001

        with (
            patch.object(uow.postgres_session, "flush", flush_mock),
            patch.object(uow.postgres_session, "refresh", refresh_mock),
        ):
            result = await instruments_repo.create(
                uow, {"ticker": "TESTTEST", "name": "Test Instrument"}
            )

    assert isinstance(result, models.Instrument)
    assert result.ticker == "TESTTEST"
    assert flush_mock.await_count == len(attempts)

    refresh_mock.assert_awaited_once()
    refresh_mock.assert_awaited_with(result)


async def test_isolation_level_serializable(db_session: AsyncSession):
    isolation = await db_session.scalar(text("SHOW transaction_isolation"))
    assert isolation == "serializable"
