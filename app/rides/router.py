from __future__ import annotations

"""
POST /v1/rides      — Create a ride request
GET  /v1/rides/{id} — Get ride status
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from app.core.dependencies import DbSession, RedisConn
from app.rides.repository import RideRepository
from app.rides.schemas import RideCreateRequest, RideResponse
from app.rides.service import run_matching
from app.trips.service import estimate_fare

router = APIRouter(prefix="/rides", tags=["rides"])

RIDE_CACHE_TTL = 30


@router.post("", status_code=status.HTTP_201_CREATED, response_model=RideResponse)
async def create_ride(
    body: RideCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: DbSession,
    redis: RedisConn,
):
    idempotency_key = request.headers.get("Idempotency-Key") or str(uuid.uuid4())

    ride_repo = RideRepository(db)
    existing = await ride_repo.get_by_idempotency_key(idempotency_key)
    if existing:
        return RideResponse.model_validate(existing)

    estimated_fare, surge_multiplier = await estimate_fare(
        redis, body.tier, body.pickup_lat, body.pickup_lng,
        body.destination_lat, body.destination_lng,
    )

    ride = await ride_repo.create(
        rider_id=body.rider_id,
        pickup_lat=body.pickup_lat,
        pickup_lng=body.pickup_lng,
        pickup_address=body.pickup_address,
        destination_lat=body.destination_lat,
        destination_lng=body.destination_lng,
        destination_address=body.destination_address,
        tier=body.tier,
        payment_method=body.payment_method,
        surge_multiplier=surge_multiplier,
        estimated_fare=estimated_fare,
        idempotency_key=idempotency_key,
        status="PENDING",
    )

    background_tasks.add_task(
        run_matching, ride.id, body.tier, body.pickup_lat, body.pickup_lng
    )

    return RideResponse.model_validate(ride)


@router.get("/{ride_id}", response_model=RideResponse)
async def get_ride(ride_id: uuid.UUID, db: DbSession, redis: RedisConn):
    cache_key = f"ride:detail:{ride_id}"
    cached = await redis.get(cache_key)
    if cached:
        return RideResponse.model_validate_json(cached)

    ride = await RideRepository(db).get_by_id(ride_id)
    if ride is None:
        raise HTTPException(status_code=404, detail="Ride not found")

    response = RideResponse.model_validate(ride)
    await redis.setex(cache_key, RIDE_CACHE_TTL, response.model_dump_json())
    return response
