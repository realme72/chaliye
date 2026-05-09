from __future__ import annotations
from enum import Enum


class DriverStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    ON_TRIP = "ON_TRIP"
