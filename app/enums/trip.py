from __future__ import annotations
from enum import Enum


class TripStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
