from __future__ import annotations

"""Unit tests for matching service state machine logic."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.ride import VALID_TRANSITIONS


def test_valid_transitions_complete():
    """Every terminal state should have no outgoing transitions."""
    assert VALID_TRANSITIONS["COMPLETED"] == set()
    assert VALID_TRANSITIONS["CANCELLED"] == set()


def test_matching_reachable_from_pending():
    assert "MATCHING" in VALID_TRANSITIONS["PENDING"]


def test_driver_assigned_reachable_from_matching():
    assert "DRIVER_ASSIGNED" in VALID_TRANSITIONS["MATCHING"]


def test_completed_reachable_from_in_progress():
    assert "COMPLETED" in VALID_TRANSITIONS["IN_PROGRESS"]


def test_invalid_transition_raises():
    from app.repositories.ride_repo import InvalidStatusTransitionError
    exc = InvalidStatusTransitionError("COMPLETED", "PENDING")
    assert "COMPLETED" in str(exc)
    assert "PENDING" in str(exc)


def test_all_statuses_present():
    expected = {"PENDING", "MATCHING", "DRIVER_ASSIGNED", "IN_PROGRESS", "COMPLETED", "CANCELLED"}
    assert set(VALID_TRANSITIONS.keys()) == expected
