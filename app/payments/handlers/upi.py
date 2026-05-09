from __future__ import annotations

"""
UPI payment handlers — one subclass per UPI app.
All share the same NPCI UPI gateway call; subclassing gives distinct display names.
"""

import httpx

from app.core.config import settings
from app.payments.handlers.base import BasePaymentHandler, PaymentResult
from app.payments.handlers.registry import PaymentRegistry


class _UPIBaseHandler(BasePaymentHandler):
    display_name = "UPI"

    async def process(self, amount: float, currency: str, payment_ref: str) -> PaymentResult:
        payload = {
            "amount": int(amount * 100),  # paise
            "currency": currency,
            "method": "UPI",
            "upi_app": self.display_name,
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
                return PaymentResult(success=True, reference=f"UPI-{ref[:20].upper()}")
            return PaymentResult(success=False, error=f"Gateway returned {resp.status_code}")
        except httpx.RequestError as exc:
            return PaymentResult(success=False, error=str(exc))


@PaymentRegistry.register("UPI_PHONEPE")
class PhonePeHandler(_UPIBaseHandler):
    display_name = "PhonePe"


@PaymentRegistry.register("UPI_GPAY")
class GooglePayHandler(_UPIBaseHandler):
    display_name = "Google Pay"


@PaymentRegistry.register("UPI_CRED")
class CREDHandler(_UPIBaseHandler):
    display_name = "CRED"


@PaymentRegistry.register("UPI_PAYTM")
class PaytmHandler(_UPIBaseHandler):
    display_name = "Paytm"


@PaymentRegistry.register("UPI_BHIM")
class BHIMHandler(_UPIBaseHandler):
    display_name = "BHIM UPI"
