from __future__ import annotations

"""POST /v1/trips/{id}/end — End an in-progress trip and calculate fare."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.core.dependencies import DbSession, RedisConn
from app.drivers.repository import DriverRepository
from app.rides.repository import RideRepository
from app.trips.repository import TripRepository
from app.trips.schemas import TripResponse
from app.trips.service import calculate_fare, haversine_km

router = APIRouter(prefix="/trips", tags=["trips"])

DRIVER_STATUS_KEY = "driver:status:{driver_id}"
RIDE_STATUS_KEY = "ride:status:{ride_id}"
RIDE_CACHE_KEY = "ride:detail:{ride_id}"


@router.post("/{trip_id}/end", response_model=TripResponse)
async def end_trip(trip_id: uuid.UUID, db: DbSession, redis: RedisConn):
    trip_repo = TripRepository(db)
    trip = await trip_repo.get_by_id(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.status != "IN_PROGRESS":
        raise HTTPException(status_code=409, detail=f"Trip is already {trip.status!r}")

    ride = await RideRepository(db).get_by_id(trip.ride_id)
    if ride is None:
        raise HTTPException(status_code=500, detail="Associated ride not found")

    distance_km = haversine_km(
        ride.pickup_lat, ride.pickup_lng,
        ride.destination_lat, ride.destination_lng,
    )

    started_at: datetime = trip.started_at  # type: ignore[assignment]
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    duration_sec = max(1, int((datetime.now(timezone.utc) - started_at).total_seconds()))

    actual_fare = calculate_fare(ride.tier, distance_km, duration_sec, ride.surge_multiplier)

    completed_trip = await trip_repo.complete(trip_id, distance_km, duration_sec, actual_fare)
    await RideRepository(db).transition_status(ride.id, "COMPLETED")

    if ride.driver_id:
        driver_repo = DriverRepository(db)
        await driver_repo.set_status(ride.driver_id, "ONLINE")
        await driver_repo.increment_trips(ride.driver_id)
        await redis.set(DRIVER_STATUS_KEY.format(driver_id=ride.driver_id), "ONLINE")

    await redis.set(RIDE_STATUS_KEY.format(ride_id=ride.id), "COMPLETED", ex=3600)
    await redis.delete(RIDE_CACHE_KEY.format(ride_id=ride.id))

    return TripResponse.model_validate(completed_trip)
