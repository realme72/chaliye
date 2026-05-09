from __future__ import annotations

"""
Centralised FastAPI dependencies.

DbSession  — one AsyncSession per request; commits on clean exit, rolls back on error.
RedisConn  — application-wide Redis client from the shared pool.
CurrentActor — actor dict set by AuthMiddleware; use in route handlers for identity checks.
"""

from typing import Annotated, AsyncIterator

import redis.asyncio as aioredis
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.redis_client import get_redis as _get_redis


async def get_db() -> AsyncIterator[AsyncSession]:
    """
    Single session for the entire request.  All repository calls in one handler
    share this session → one transaction, one atomic commit or rollback.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_redis() -> aioredis.Redis:
    return await _get_redis()


def get_current_actor(request: Request) -> dict:
    """Returns the actor dict injected by AuthMiddleware: {id, type, name}."""
    return request.state.actor


# ── Annotated aliases ──────────────────────────────────────────────────────
DbSession = Annotated[AsyncSession, Depends(get_db)]
RedisConn = Annotated[aioredis.Redis, Depends(get_redis)]
CurrentActor = Annotated[dict, Depends(get_current_actor)]
