from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.trips.models import Trip


class TripRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, ride_id: uuid.UUID) -> Trip:
        trip = Trip(
            ride_id=ride_id,
            status="IN_PROGRESS",
            started_at=datetime.now(timezone.utc),
        )
        self._session.add(trip)
        await self._session.flush()
        await self._session.refresh(trip)
        return trip

    async def get_by_id(self, trip_id: uuid.UUID) -> Optional[Trip]:
        result = await self._session.execute(
            select(Trip).where(Trip.id == trip_id)
        )
        return result.scalar_one_or_none()

    async def get_by_ride_id(self, ride_id: uuid.UUID) -> Optional[Trip]:
        result = await self._session.execute(
            select(Trip).where(Trip.ride_id == ride_id)
        )
        return result.scalar_one_or_none()

    async def complete(
        self,
        trip_id: uuid.UUID,
        distance_km: float,
        duration_sec: int,
        actual_fare: float,
    ) -> Trip:
        await self._session.execute(
            update(Trip)
            .where(Trip.id == trip_id)
            .values(
                status="COMPLETED",
                ended_at=datetime.now(timezone.utc),
                distance_km=distance_km,
                duration_sec=duration_sec,
                actual_fare=actual_fare,
            )
        )
        await self._session.flush()
        return await self.get_by_id(trip_id)  # type: ignore[return-value]
