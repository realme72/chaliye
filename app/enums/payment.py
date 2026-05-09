from __future__ import annotations
from enum import Enum


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PaymentMethod(str, Enum):
    CASH = "CASH"
    UPI_PHONEPE = "UPI_PHONEPE"
    UPI_GPAY = "UPI_GPAY"
    UPI_CRED = "UPI_CRED"
    UPI_PAYTM = "UPI_PAYTM"
    UPI_BHIM = "UPI_BHIM"
    CARD = "CARD"
