from __future__ import annotations

import uuid

from sqlalchemy import Float, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, TimestampMixin


class Driver(Base, TimestampMixin):
    __tablename__ = "drivers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(64), nullable=False)
    tier: Mapped[str] = mapped_column(String(16), nullable=False)  # ECONOMY|PREMIUM|LUXURY
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OFFLINE")
    rating: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    total_trips: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    api_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    rides = relationship("Ride", back_populates="driver", foreign_keys="Ride.driver_id")

    __table_args__ = (
        Index("ix_drivers_status_tier", "status", "tier"),
        Index("ix_drivers_api_key", "api_key"),
    )
