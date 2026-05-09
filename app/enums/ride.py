from __future__ import annotations
from enum import Enum


class RideStatus(str, Enum):
    PENDING = "PENDING"
    MATCHING = "MATCHING"
    DRIVER_ASSIGNED = "DRIVER_ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class RideTier(str, Enum):
    ECONOMY = "ECONOMY"
    PREMIUM = "PREMIUM"
    LUXURY = "LUXURY"


# Valid state-machine transitions (string keys match DB-stored values).
# DRIVER_ASSIGNED → COMPLETED is allowed because there is no explicit
# start-trip API; the trip begins implicitly on acceptance.
RIDE_STATE_TRANSITIONS: dict[str, set[str]] = {
    "PENDING":         {"MATCHING", "CANCELLED"},
    "MATCHING":        {"DRIVER_ASSIGNED", "CANCELLED"},
    "DRIVER_ASSIGNED": {"IN_PROGRESS", "MATCHING", "CANCELLED", "COMPLETED"},
    "IN_PROGRESS":     {"COMPLETED", "CANCELLED"},
    "COMPLETED":       set(),
    "CANCELLED":       set(),
}
