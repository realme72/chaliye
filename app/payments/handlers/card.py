from __future__ import annotations

import httpx

from app.core.config import settings
from app.payments.handlers.base import BasePaymentHandler, PaymentResult
from app.payments.handlers.registry import PaymentRegistry


@PaymentRegistry.register("CARD")
class CardPaymentHandler(BasePaymentHandler):
    display_name = "Card"

    async def process(self, amount: float, currency: str, payment_ref: str) -> PaymentResult:
        payload = {
            "amount": int(amount * 100),
            "currency": currency,
            "method": "CARD",
            "payment_ref": payment_ref,
        }
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    settings.psp_base_url,
                    json=payload,
                    headers={"Authorization": f"Bearer {settings.psp_api_key}"},
                )
            if resp.status_code in (200, 201):
                ref = resp.json().get("json", {}).get("payment_ref") or payment_ref
                return PaymentResult(success=True, reference=f"CARD-{ref[:20].upper()}")
            return PaymentResult(success=False, error=f"Gateway returned {resp.status_code}")
        except httpx.RequestError as exc:
            return PaymentResult(success=False, error=str(exc))
