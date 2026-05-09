from __future__ import annotations

"""
Sliding-window rate limiter using Redis sorted sets.

Algorithm:
  For each request, within a pipeline:
    1. ZREMRANGEBYSCORE key -inf (now - window_sec)  — evict stale timestamps
    2. ZADD key now now                               — record this request
    3. ZCARD key                                      — count requests in window
    4. EXPIRE key window_sec                          — TTL cleanup

  If count > limit → 429 Too Many Requests.

Rate key: per authenticated actor when available, otherwise per client IP.
Default limit: 100 req / 60 s.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)

WINDOW_SEC = 60
MAX_REQUESTS = 100
EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        identifier = self._get_identifier(request)
        rate_key = f"rate:{identifier}"

        allowed, count = await self._check_rate(rate_key)
        if not allowed:
            logger.warning("Rate limit exceeded for %s (%d/%d)", identifier, count, MAX_REQUESTS)
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded: {MAX_REQUESTS} requests per {WINDOW_SEC}s"},
                headers={"Retry-After": str(WINDOW_SEC)},
            )

        return await call_next(request)

    @staticmethod
    def _get_identifier(request: Request) -> str:
        actor = getattr(request.state, "actor", None)
        if actor:
            return actor["id"]
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    @staticmethod
    async def _check_rate(key: str) -> tuple[bool, int]:
        redis = await get_redis()
        now = time.time()
        window_start = now - WINDOW_SEC

        async with redis.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, "-inf", window_start)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, WINDOW_SEC)
            results = await pipe.execute()

        count: int = results[2]
        return count <= MAX_REQUESTS, count
