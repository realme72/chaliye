from __future__ import annotations

"""
Payment flow:
  1. Generate a deterministic payment_ref server-side:
       sha256(f"{rider_id}:{trip_id}:{payment_method}:{date}")[:40]
  2. Check Redis first (payment:{ref}) — avoids DB round-trip on duplicate requests.
  3. DB fallback if Redis key has expired.
  4. No client-provided idempotency key stored in DB.
"""

import hashlib
import json
import logging
from datetime import date
from typing import Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

PAYMENT_CACHE_TTL = 86400  # 24 h


def generate_payment_ref(rider_id: str, trip_id: str, payment_method: str) -> str:
    raw = f"{rider_id}:{trip_id}:{payment_method.upper()}:{date.today().isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:40]


async def get_cached_payment(redis: aioredis.Redis, payment_ref: str) -> Optional[dict]:
    data = await redis.get(f"payment:{payment_ref}")
    if data:
        return json.loads(data)
    return None


async def cache_payment(redis: aioredis.Redis, payment_ref: str, payload: dict) -> None:
    await redis.setex(f"payment:{payment_ref}", PAYMENT_CACHE_TTL, json.dumps(payload))


async def invalidate_payment_cache(redis: aioredis.Redis, payment_ref: str) -> None:
    await redis.delete(f"payment:{payment_ref}")
