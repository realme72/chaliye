from __future__ import annotations

from app.payments.handlers.base import BasePaymentHandler, PaymentResult
from app.payments.handlers.registry import PaymentRegistry


@PaymentRegistry.register("CASH")
class CashPaymentHandler(BasePaymentHandler):
    display_name = "Cash"

    @property
    def is_offline(self) -> bool:
        return True

    async def process(self, amount: float, currency: str, payment_ref: str) -> PaymentResult:
        return PaymentResult(
            success=True,
            reference=f"CASH-{payment_ref[:20].upper()}",
        )
