from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.drivers.models import Driver


class DriverRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, driver_id: uuid.UUID) -> Optional[Driver]:
        result = await self._session.execute(
            select(Driver).where(Driver.id == driver_id)
        )
        return result.scalar_one_or_none()

    async def get_by_api_key(self, api_key: str) -> Optional[Driver]:
        result = await self._session.execute(
            select(Driver).where(Driver.api_key == api_key)
        )
        return result.scalar_one_or_none()

    async def set_status(self, driver_id: uuid.UUID, status: str) -> None:
        await self._session.execute(
            update(Driver).where(Driver.id == driver_id).values(status=status)
        )
        await self._session.flush()

    async def increment_trips(self, driver_id: uuid.UUID) -> None:
        await self._session.execute(
            update(Driver)
            .where(Driver.id == driver_id)
            .values(total_trips=Driver.total_trips + 1)
        )
        await self._session.flush()
