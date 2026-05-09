from __future__ import annotations

"""POST /v1/payments — Trigger the payment flow for a completed trip."""

from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import DbSession, RedisConn
from app.payments.handlers import cash, upi, card  # noqa: F401 — register handlers
from app.payments.handlers.registry import PaymentRegistry
from app.payments.repository import PaymentRepository
from app.payments.schemas import PaymentRequest, PaymentResponse
from app.payments.service import cache_payment, get_cached_payment
from app.trips.repository import TripRepository

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=PaymentResponse)
async def trigger_payment(body: PaymentRequest, db: DbSession, redis: RedisConn):
    """
    Trigger payment for a completed trip.

    Idempotency is Redis-first, no idempotency key stored in DB:
      - Redis key: payment:{trip_id}  TTL: 24h
      - Redis hit → return cached response immediately
      - Redis miss → DB fallback via trip_id + rider_id + payment_method
      - Neither → create new payment record

    Payment routing:
      CASH    → offline (no PSP, no retries)
      UPI_*   → NPCI UPI gateway, 3× exponential-backoff retry
      CARD    → card gateway, 3× exponential-backoff retry
    """
    trip_id = str(body.trip_id)

    # 1. Redis-first idempotency check
    cached = await get_cached_payment(redis, trip_id)
    if cached:
        return PaymentResponse(**cached)

    payment_repo = PaymentRepository(db)

    # 2. DB fallback when Redis TTL expired
    existing = await payment_repo.get_by_trip_and_method(
        body.trip_id, body.rider_id, body.payment_method
    )
    if existing:
        response = PaymentResponse.model_validate(existing)
        await cache_payment(redis, trip_id, response.model_dump())
        return response

    # 3. New payment
    trip = await TripRepository(db).get_by_id(body.trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.status != "COMPLETED":
        raise HTTPException(
            status_code=409,
            detail=f"Trip must be COMPLETED before payment; current status: {trip.status!r}",
        )
    if trip.actual_fare is None:
        raise HTTPException(status_code=500, detail="Trip fare not yet calculated")

    payment = await payment_repo.create(
        trip_id=body.trip_id,
        rider_id=body.rider_id,
        amount=trip.actual_fare,
        currency="INR",
        status="PENDING",
        payment_method=body.payment_method,
    )
    payment = await payment_repo.update_status(payment.id, "PROCESSING")

    result = await PaymentRegistry.process(
        method=body.payment_method,
        amount=trip.actual_fare,
        currency="INR",
        payment_ref=trip_id,
    )

    final_status = "COMPLETED" if result.success else "FAILED"
    payment = await payment_repo.update_status(
        payment.id,
        final_status,
        psp_reference=result.reference,
        retry_count=1 if result.success else 3,
    )

    response = PaymentResponse.model_validate(payment)

    if not result.success:
        raise HTTPException(
            status_code=502,
            detail=f"Payment failed: {result.error or 'PSP error'}. Please try again.",
        )

    await cache_payment(redis, trip_id, response.model_dump())
    return response
