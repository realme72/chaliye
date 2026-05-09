from __future__ import annotations

"""
Auth middleware — validates the X-API-Key header on every request.

Lookup order (fastest first):
  1. Redis cache  key: auth:actor:{api_key}  TTL: 5 min
  2. riders table
  3. drivers table

Sets request.state.actor = {"id": str(uuid), "type": "rider"|"driver", "name": str}
Returns 401 if the key is missing or not found in either table.

Paths exempt from auth: /health, /docs, /openapi.json, /redoc
"""

import json
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.core.database import session_context
from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 minutes
EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "X-API-Key header is required"},
            )

        actor = await self._resolve_actor(api_key)
        if actor is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key"},
            )

        request.state.actor = actor
        return await call_next(request)

    async def _resolve_actor(self, api_key: str) -> dict | None:
        redis = await get_redis()
        cache_key = f"auth:actor:{api_key}"

        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)

        actor = await self._lookup_db(api_key)
        if actor:
            await redis.setex(cache_key, CACHE_TTL, json.dumps(actor))

        return actor

    @staticmethod
    async def _lookup_db(api_key: str) -> dict | None:
        # Import here to avoid circular imports at module load time
        from sqlalchemy import select
        from app.riders.models import Rider
        from app.drivers.models import Driver

        async with session_context() as session:
            row = await session.execute(
                select(Rider.id, Rider.name).where(Rider.api_key == api_key)
            )
            rider = row.one_or_none()
            if rider:
                return {"id": str(rider.id), "type": "rider", "name": rider.name}

            row = await session.execute(
                select(Driver.id, Driver.name).where(Driver.api_key == api_key)
            )
            driver = row.one_or_none()
            if driver:
                return {"id": str(driver.id), "type": "driver", "name": driver.name}

        return None
