from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, TimestampMixin
from app.enums.ride import RideStatus, RIDE_STATE_TRANSITIONS


class Ride(Base, TimestampMixin):
    __tablename__ = "rides"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("riders.id"), nullable=False
    )
    driver_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=True
    )

    pickup_lat: Mapped[float] = mapped_column(Float, nullable=False)
    pickup_lng: Mapped[float] = mapped_column(Float, nullable=False)
    pickup_address: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    destination_lat: Mapped[float] = mapped_column(Float, nullable=False)
    destination_lng: Mapped[float] = mapped_column(Float, nullable=False)
    destination_address: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    tier: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=RideStatus.PENDING.value)
    payment_method: Mapped[str] = mapped_column(String(16), nullable=False, default="CASH")

    surge_multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    estimated_fare: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)

    rider = relationship("Rider", back_populates="rides")
    driver = relationship("Driver", back_populates="rides", foreign_keys=[driver_id])
    trip = relationship("Trip", back_populates="ride", uselist=False)

    __table_args__ = (
        Index("ix_rides_status", "status"),
        Index("ix_rides_rider_id", "rider_id"),
        Index("ix_rides_driver_id", "driver_id"),
        Index("ix_rides_idempotency_key", "idempotency_key"),
    )
