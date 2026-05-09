from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums.ride import RIDE_STATE_TRANSITIONS
from app.rides.models import Ride


class InvalidStatusTransitionError(Exception):
    def __init__(self, from_status: str, to_status: str):
        super().__init__(f"Cannot transition ride from {from_status!r} to {to_status!r}")


class RideRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs) -> Ride:
        ride = Ride(**kwargs)
        self._session.add(ride)
        await self._session.flush()
        await self._session.refresh(ride)
        return ride

    async def get_by_id(self, ride_id: uuid.UUID) -> Optional[Ride]:
        result = await self._session.execute(
            select(Ride)
            .where(Ride.id == ride_id)
            .options(selectinload(Ride.driver), selectinload(Ride.rider))
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> Optional[Ride]:
        result = await self._session.execute(
            select(Ride).where(Ride.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def transition_status(
        self,
        ride_id: uuid.UUID,
        new_status: str,
        extra: Optional[dict] = None,
    ) -> Ride:
        ride = await self.get_by_id(ride_id)
        if ride is None:
            raise ValueError(f"Ride {ride_id} not found")

        allowed = RIDE_STATE_TRANSITIONS.get(ride.status, set())
        if new_status not in allowed:
            raise InvalidStatusTransitionError(ride.status, new_status)

        values: dict = {"status": new_status}
        if extra:
            values.update(extra)

        await self._session.execute(
            update(Ride).where(Ride.id == ride_id).values(**values)
        )
        await self._session.flush()
        await self._session.refresh(ride)
        return ride

    async def assign_driver(self, ride_id: uuid.UUID, driver_id: uuid.UUID) -> Ride:
        return await self.transition_status(
            ride_id,
            "DRIVER_ASSIGNED",
            extra={"driver_id": driver_id},
        )
