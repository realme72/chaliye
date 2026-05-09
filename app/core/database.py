from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def session_context() -> AsyncIterator[AsyncSession]:
    """
    Transaction-scoped session for use outside FastAPI's dependency injection
    (e.g. background tasks, scripts).

    Commits on clean exit, rolls back on exception — mirrors the behaviour of
    the get_db dependency so repositories behave consistently regardless of
    who is calling them.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
