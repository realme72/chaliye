from __future__ import annotations

"""
Payment Handler Registry — maps payment method strings to handler classes.

Adding a new payment method requires only:
  1. Create a handler extending BasePaymentHandler.
  2. Decorate it with @PaymentRegistry.register("METHOD_NAME").
"""

import asyncio
import logging
from typing import Callable, Type

from app.payments.handlers.base import BasePaymentHandler, PaymentResult

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_BASE = 2.0


class PaymentRegistry:
    _handlers: dict[str, Type[BasePaymentHandler]] = {}

    @classmethod
    def register(cls, method: str) -> Callable:
        def decorator(handler_cls: Type[BasePaymentHandler]) -> Type[BasePaymentHandler]:
            cls._handlers[method.upper()] = handler_cls
            logger.debug("Registered payment handler: %s → %s", method, handler_cls.__name__)
            return handler_cls
        return decorator

    @classmethod
    def get_handler(cls, method: str) -> BasePaymentHandler:
        handler_cls = cls._handlers.get(method.upper())
        if handler_cls is None:
            available = ", ".join(sorted(cls._handlers))
            raise ValueError(f"Unsupported payment method {method!r}. Available: {available}")
        return handler_cls()

    @classmethod
    def supported_methods(cls) -> list[str]:
        return sorted(cls._handlers.keys())

    @classmethod
    async def process(
        cls,
        method: str,
        amount: float,
        currency: str,
        payment_ref: str,
    ) -> PaymentResult:
        handler = cls.get_handler(method)

        if handler.is_offline:
            result = await handler.process(amount, currency, payment_ref)
            logger.info("Offline payment (%s) recorded: ref=%s", handler.display_name, result.reference)
            return result

        last_result = PaymentResult(success=False, error="No attempts made")
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                last_result = await handler.process(amount, currency, payment_ref)
            except Exception as exc:
                last_result = PaymentResult(success=False, error=str(exc))
                logger.warning("%s attempt %d/%d raised: %s", handler.display_name, attempt, MAX_RETRIES, exc)

            if last_result.success:
                logger.info("%s payment succeeded on attempt %d: ref=%s", handler.display_name, attempt, last_result.reference)
                return last_result

            if attempt < MAX_RETRIES:
                wait = BACKOFF_BASE ** attempt
                logger.warning("%s attempt %d/%d failed, retrying in %.1fs", handler.display_name, attempt, MAX_RETRIES, wait)
                await asyncio.sleep(wait)

        logger.error("%s payment failed after %d attempts", handler.display_name, MAX_RETRIES)
        return last_result
