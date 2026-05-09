from __future__ import annotations

import math

import redis.asyncio as aioredis

TIER_RATES: dict[str, dict] = {
    "ECONOMY": {"base": 30.0, "per_km": 12.0, "per_min": 2.0, "min_fare": 50.0},
    "PREMIUM": {"base": 60.0, "per_km": 20.0, "per_min": 3.0, "min_fare": 100.0},
    "LUXURY":  {"base": 120.0, "per_km": 35.0, "per_min": 5.0, "min_fare": 200.0},
}

SURGE_ZONE_KEY = "surge:zone:{geohash}"
SURGE_MAX = 3.0


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _geohash_prefix(lat: float, lng: float, precision: int = 5) -> str:
    step = 360.0 / (2 ** precision)
    col = int((lng + 180) / step)
    row = int((lat + 90) / step)
    return f"{row}:{col}"


def calculate_fare(
    tier: str,
    distance_km: float,
    duration_sec: int,
    surge_multiplier: float = 1.0,
) -> float:
    rates = TIER_RATES.get(tier, TIER_RATES["ECONOMY"])
    duration_min = duration_sec / 60.0
    raw = rates["base"] + rates["per_km"] * distance_km + rates["per_min"] * duration_min
    fare = max(raw, rates["min_fare"]) * surge_multiplier
    return round(fare, 2)


async def get_surge_multiplier(redis: aioredis.Redis, lat: float, lng: float) -> float:
    key = SURGE_ZONE_KEY.format(geohash=_geohash_prefix(lat, lng))
    val = await redis.get(key)
    if val is None:
        return 1.0
    try:
        return min(float(val), SURGE_MAX)
    except (ValueError, TypeError):
        return 1.0


async def estimate_fare(
    redis: aioredis.Redis,
    tier: str,
    pickup_lat: float,
    pickup_lng: float,
    dest_lat: float,
    dest_lng: float,
) -> tuple[float, float]:
    surge = await get_surge_multiplier(redis, pickup_lat, pickup_lng)
    distance_km = haversine_km(pickup_lat, pickup_lng, dest_lat, dest_lng)
    estimated_duration_sec = int((distance_km / 30.0) * 3600)
    fare = calculate_fare(tier, distance_km, estimated_duration_sec, surge)
    return fare, surge
