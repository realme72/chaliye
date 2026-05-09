from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.payments.models import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs) -> Payment:
        payment = Payment(**kwargs)
        self._session.add(payment)
        await self._session.flush()
        await self._session.refresh(payment)
        return payment

    async def get_by_id(self, payment_id: uuid.UUID) -> Optional[Payment]:
        result = await self._session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_trip_and_method(
        self, trip_id: uuid.UUID, rider_id: uuid.UUID, payment_method: str
    ) -> Optional[Payment]:
        """DB fallback for idempotency when Redis TTL has expired."""
        result = await self._session.execute(
            select(Payment).where(
                Payment.trip_id == trip_id,
                Payment.rider_id == rider_id,
                Payment.payment_method == payment_method,
            )
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        payment_id: uuid.UUID,
        status: str,
        psp_reference: Optional[str] = None,
        retry_count: Optional[int] = None,
    ) -> Payment:
        values: dict = {"status": status}
        if psp_reference is not None:
            values["psp_reference"] = psp_reference
        if retry_count is not None:
            values["retry_count"] = retry_count

        await self._session.execute(
            update(Payment).where(Payment.id == payment_id).values(**values)
        )
        await self._session.flush()
        return await self.get_by_id(payment_id)  # type: ignore[return-value]
