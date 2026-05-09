from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, field_validator


class PaymentRequest(BaseModel):
    trip_id: uuid.UUID
    rider_id: uuid.UUID
    payment_method: str

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: str) -> str:
        from app.payments.handlers.registry import PaymentRegistry
        supported = PaymentRegistry.supported_methods()
        if v.upper() not in supported:
            raise ValueError(f"payment_method must be one of {supported}")
        return v.upper()


class PaymentResponse(BaseModel):
    id: uuid.UUID
    trip_id: uuid.UUID
    amount: float
    currency: str
    status: str
    payment_method: str
    psp_reference: Optional[str]
    retry_count: int

    model_config = {"from_attributes": True}
