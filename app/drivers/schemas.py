from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class LocationUpdateRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class AcceptRideRequest(BaseModel):
    ride_id: uuid.UUID


class DriverResponse(BaseModel):
    id: uuid.UUID
    name: str
    tier: str
    status: str
    rating: float

    model_config = {"from_attributes": True}
