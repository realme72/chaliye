from __future__ import annotations

"""
Matching service — nearest-first geo search with radius expansion.

Flow (runs as asyncio background task):
  1. PENDING → MATCHING
  2. For each radius tier [2 km, 5 km, 10 km]:
       a. GEOSEARCH for ONLINE drivers with matching tier
       b. Offer the ride to the nearest un-offered driver
          (set Redis key ride:offer:{ride_id} = driver_id, TTL = 30 s)
       c. Poll for 30 s; if driver calls /accept → DRIVER_ASSIGNED, exit.
       d. If offer TTL expires, try next driver.
  3. All radii exhausted → CANCELLED.
"""

import asyncio
import logging
import uuid

import redis.asyncio as aioredis

from app.core.database import session_context
from app.core.redis_client import get_redis
from app.rides.repository import RideRepository
from app.drivers.repository import DriverRepository

logger = logging.getLogger(__name__)

GEO_KEY = "geo:drivers:{tier}"
DRIVER_STATUS_KEY = "driver:status:{driver_id}"
OFFER_KEY = "ride:offer:{ride_id}"
OFFERED_FLAG_KEY = "offered:{ride_id}:{driver_id}"
RIDE_STATUS_KEY = "ride:status:{ride_id}"

RADII_KM = [2.0, 5.0, 10.0]
OFFER_TTL = 120  # seconds driver has to accept
BETWEEN_RADIUS_WAIT = 5


async def run_matching(
    ride_id: uuid.UUID,
    tier: str,
    pickup_lat: float,
    pickup_lng: float,
) -> None:
    redis = await get_redis()

    async with session_context() as session:
        repo = RideRepository(session)
        try:
            await repo.transition_status(ride_id, "MATCHING")
        except Exception:
            logger.exception("Failed to transition ride %s to MATCHING", ride_id)
            return

    await redis.set(RIDE_STATUS_KEY.format(ride_id=ride_id), "MATCHING", ex=600)

    for radius_km in RADII_KM:
        matched = await _try_radius(redis, ride_id, tier, pickup_lat, pickup_lng, radius_km)
        if matched:
            return

        current_status = await redis.get(RIDE_STATUS_KEY.format(ride_id=ride_id))
        if current_status and current_status != "MATCHING":
            return

        await asyncio.sleep(BETWEEN_RADIUS_WAIT)

    logger.warning("No drivers found for ride %s, cancelling", ride_id)
    async with session_context() as session:
        repo = RideRepository(session)
        try:
            await repo.transition_status(
                ride_id,
                "CANCELLED",
                extra={"cancellation_reason": "No drivers available"},
            )
        except Exception:
            logger.exception("Failed to cancel ride %s", ride_id)
    await redis.set(RIDE_STATUS_KEY.format(ride_id=ride_id), "CANCELLED", ex=3600)


async def _try_radius(
    redis: aioredis.Redis,
    ride_id: uuid.UUID,
    tier: str,
    lat: float,
    lng: float,
    radius_km: float,
) -> bool:
    try:
        candidates: list[str] = await redis.geosearch(
            GEO_KEY.format(tier=tier),
            longitude=lng,
            latitude=lat,
            unit="km",
            radius=radius_km,
            sort="ASC",
            count=30,
        )
    except Exception:
        logger.exception("Redis geosearch failed for ride %s", ride_id)
        return False

    for driver_id_str in candidates:
        already_offered = await redis.exists(
            OFFERED_FLAG_KEY.format(ride_id=ride_id, driver_id=driver_id_str)
        )
        if already_offered:
            continue

        drv_status = await redis.get(DRIVER_STATUS_KEY.format(driver_id=driver_id_str))
        if drv_status != "ONLINE":
            continue

        await redis.setex(
            OFFERED_FLAG_KEY.format(ride_id=ride_id, driver_id=driver_id_str),
            600,
            "1",
        )
        await redis.setex(
            OFFER_KEY.format(ride_id=ride_id),
            OFFER_TTL,
            driver_id_str,
        )

        logger.info("Offered ride %s to driver %s (radius %.1f km)", ride_id, driver_id_str, radius_km)

        accepted = await _poll_for_acceptance(redis, ride_id, OFFER_TTL)
        if accepted:
            return True

        await redis.delete(OFFER_KEY.format(ride_id=ride_id))

    return False


async def _poll_for_acceptance(
    redis: aioredis.Redis,
    ride_id: uuid.UUID,
    timeout_sec: int,
) -> bool:
    deadline = asyncio.get_event_loop().time() + timeout_sec
    while asyncio.get_event_loop().time() < deadline:
        status = await redis.get(RIDE_STATUS_KEY.format(ride_id=ride_id))
        if status and status != "MATCHING":
            return status == "DRIVER_ASSIGNED"
        await asyncio.sleep(1.0)
    return False
