import asyncpg
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_fixed, wait_random

from src.core import db


class UnitOfWork:
    def __init__(self, *, use_postgres: bool = True, max_retries: int = 5):
        self._use_postgres = use_postgres
        self._max_retries = max_retries
        self._postgres_manager = db.get_postgres_manager() if use_postgres else None
        self._postgres_session = None

    @classmethod
    async def _is_serialization_error(cls, exc):
        return isinstance(exc, (DBAPIError, OperationalError)) and isinstance(
            exc.orig, asyncpg.exceptions.SerializationError
        )

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(0.1) + wait_random(0.3, 1),
        retry=retry_if_exception(lambda e: isinstance(e, asyncpg.exceptions.SerializationError)),
        reraise=True,
    )
    async def __aenter__(self):
        if self._postgres_manager:
            self._postgres_session = await self._postgres_manager.get_session()
            await self._postgres_session.begin()
        return self

    async def __aexit__(self, exc_type=None, exc=None, tb=None):
        try:
            if self._postgres_session:
                if exc_type is not None:
                    await self._postgres_session.rollback()
                else:
                    try:
                        await self._postgres_session.commit()
                    except Exception as commit_ex:
                        await self._postgres_session.rollback()
                        if self._is_serialization_error(commit_ex):
                            raise  # Will be caught by tenacity
                        raise
        finally:
            if self._postgres_session:
                await self._postgres_session.close()
            self._postgres_session = None

    @property
    def postgres_session(self) -> AsyncSession:
        assert self._postgres_session is not None
        return self._postgres_session
