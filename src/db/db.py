from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.config import get_settings

settings = get_settings()

if settings.DEBUG:
    engine = create_async_engine(
        str(settings.DATABASE_URL), echo=False, poolclass=NullPool, future=True
    )
else:  # pragma: no cover
    engine = create_async_engine(str(settings.DATABASE_URL), echo=False)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@asynccontextmanager
async def get_transaction_session() -> AsyncGenerator[Any, Any]:
    async with async_session_factory() as session:
        async with session.begin():
            yield session
