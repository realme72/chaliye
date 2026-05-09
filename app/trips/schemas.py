from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel


class TripResponse(BaseModel):
    id: uuid.UUID
    ride_id: uuid.UUID
    status: str
    distance_km: Optional[float]
    duration_sec: Optional[int]
    actual_fare: Optional[float]

    model_config = {"from_attributes": True}
