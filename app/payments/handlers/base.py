from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class PaymentResult:
    success: bool
    reference: Optional[str] = None
    error: Optional[str] = None


class BasePaymentHandler(ABC):
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name shown in receipts and logs."""

    @property
    def is_offline(self) -> bool:
        """Cash overrides this to skip PSP calls and retries."""
        return False

    @abstractmethod
    async def process(
        self,
        amount: float,
        currency: str,
        payment_ref: str,
    ) -> PaymentResult:
        """Execute the payment. Return PaymentResult(success=True/False, ...)."""
