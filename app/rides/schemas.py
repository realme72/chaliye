from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, Field, field_validator

VALID_TIERS = {"ECONOMY", "PREMIUM", "LUXURY"}


class RideCreateRequest(BaseModel):
    rider_id: uuid.UUID
    pickup_lat: float = Field(..., ge=-90, le=90)
    pickup_lng: float = Field(..., ge=-180, le=180)
    pickup_address: Optional[str] = None
    destination_lat: float = Field(..., ge=-90, le=90)
    destination_lng: float = Field(..., ge=-180, le=180)
    destination_address: Optional[str] = None
    tier: str = "ECONOMY"
    payment_method: str = "CASH"

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, v: str) -> str:
        if v.upper() not in VALID_TIERS:
            raise ValueError(f"tier must be one of {sorted(VALID_TIERS)}")
        return v.upper()

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: str) -> str:
        from app.payments.handlers.registry import PaymentRegistry
        supported = PaymentRegistry.supported_methods()
        if v.upper() not in supported:
            raise ValueError(f"payment_method must be one of {supported}")
        return v.upper()


class RideResponse(BaseModel):
    id: uuid.UUID
    rider_id: uuid.UUID
    driver_id: Optional[uuid.UUID]
    pickup_lat: float
    pickup_lng: float
    pickup_address: Optional[str]
    destination_lat: float
    destination_lng: float
    destination_address: Optional[str]
    tier: str
    status: str
    payment_method: str
    surge_multiplier: float
    estimated_fare: Optional[float]
    cancellation_reason: Optional[str]

    model_config = {"from_attributes": True}
