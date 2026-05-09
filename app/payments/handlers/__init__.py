from app.payments.handlers import cash, upi, card  # noqa: F401 — triggers handler registration

__all__ = ["cash", "upi", "card"]
