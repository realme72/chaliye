from __future__ import annotations

"""
POST /v1/drivers/{id}/location — Send driver location update
POST /v1/drivers/{id}/accept  — Accept ride assignment
"""

import uuid

from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import DbSession, RedisConn
from app.drivers.repository import DriverRepository
from app.drivers.schemas import AcceptRideRequest, LocationUpdateRequest
from app.rides.repository import InvalidStatusTransitionError, RideRepository
from app.rides.schemas import RideResponse
from app.trips.repository import TripRepository

router = APIRouter(prefix="/drivers", tags=["drivers"])

GEO_KEY = "geo:drivers:{tier}"
DRIVER_STATUS_KEY = "driver:status:{driver_id}"
DRIVER_LOCATION_KEY = "driver:location:{driver_id}"
OFFER_KEY = "ride:offer:{ride_id}"
RIDE_STATUS_KEY = "ride:status:{ride_id}"
ASSIGN_LOCK_KEY = "ride:assign:lock:{ride_id}"
RIDE_CACHE_KEY = "ride:detail:{ride_id}"


@router.post("/{driver_id}/location", status_code=status.HTTP_204_NO_CONTENT)
async def update_location(
    driver_id: uuid.UUID,
    body: LocationUpdateRequest,
    db: DbSession,
    redis: RedisConn,
):
    """
    High-throughput GPS ingest: writes only to Redis, no DB write per update.
    Redis GEO set enables O(log N) radius search in the matching service.
    """
    driver = await DriverRepository(db).get_by_id(driver_id)
    if driver is None:
        raise HTTPException(status_code=404, detail="Driver not found")

    await redis.geoadd(
        GEO_KEY.format(tier=driver.tier),
        [body.longitude, body.latitude, str(driver_id)],
    )
    await redis.hset(
        DRIVER_LOCATION_KEY.format(driver_id=driver_id),
        mapping={"lat": body.latitude, "lng": body.longitude},
    )
    current = await redis.get(DRIVER_STATUS_KEY.format(driver_id=driver_id))
    if current is None:
        await redis.set(DRIVER_STATUS_KEY.format(driver_id=driver_id), driver.status)


@router.post("/{driver_id}/accept", response_model=RideResponse)
async def accept_ride(
    driver_id: uuid.UUID,
    body: AcceptRideRequest,
    db: DbSession,
    redis: RedisConn,
):
    """
    Accept a pending ride offer.

    Concurrency safety: Redis SET NX distributed lock prevents two simultaneous
    accepts from both winning the same ride.
    All DB mutations share the single session → one atomic commit at request end.
    """
    driver = await DriverRepository(db).get_by_id(driver_id)
    if driver is None:
        raise HTTPException(status_code=404, detail="Driver not found")

    offered_to = await redis.get(OFFER_KEY.format(ride_id=body.ride_id))
    if offered_to != str(driver_id):
        raise HTTPException(
            status_code=409,
            detail="No active offer for this driver on this ride, or offer has expired",
        )

    lock_key = ASSIGN_LOCK_KEY.format(ride_id=body.ride_id)
    acquired = await redis.set(lock_key, str(driver_id), nx=True, ex=10)
    if not acquired:
        raise HTTPException(status_code=409, detail="Ride is being assigned to another driver")

    try:
        ride_repo = RideRepository(db)
        try:
            ride = await ride_repo.assign_driver(body.ride_id, driver_id)
            await TripRepository(db).create(ride_id=ride.id)
            await DriverRepository(db).set_status(driver_id, "ON_TRIP")
        except InvalidStatusTransitionError:
            raise HTTPException(status_code=409, detail="Ride is no longer in MATCHING state")

        await redis.set(DRIVER_STATUS_KEY.format(driver_id=driver_id), "ON_TRIP")
        await redis.set(RIDE_STATUS_KEY.format(ride_id=body.ride_id), "DRIVER_ASSIGNED", ex=3600)
        await redis.delete(RIDE_CACHE_KEY.format(ride_id=body.ride_id))

        return RideResponse.model_validate(ride)
    finally:
        await redis.delete(lock_key)
