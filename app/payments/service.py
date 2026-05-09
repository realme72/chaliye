from __future__ import annotations

import json
from typing import Optional

import redis.asyncio as aioredis

PAYMENT_CACHE_TTL = 86400  # 24 h


async def get_cached_payment(redis: aioredis.Redis, trip_id: str) -> Optional[dict]:
    data = await redis.get(f"payment:{trip_id}")
    if data:
        return json.loads(data)
    return None


async def cache_payment(redis: aioredis.Redis, trip_id: str, payload: dict) -> None:
    await redis.setex(f"payment:{trip_id}", PAYMENT_CACHE_TTL, json.dumps(payload))
