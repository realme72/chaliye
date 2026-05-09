from __future__ import annotations

"""Unit tests for the pricing service (no I/O required)."""

import pytest

from app.services.pricing_service import haversine_km, calculate_fare, TIER_RATES


def test_haversine_same_point():
    assert haversine_km(12.9716, 77.5946, 12.9716, 77.5946) == pytest.approx(0.0, abs=1e-6)


def test_haversine_known_distance():
    # Bangalore to Mumbai ~840 km
    dist = haversine_km(12.9716, 77.5946, 19.0760, 72.8777)
    assert 830 < dist < 860


def test_calculate_fare_minimum_applies():
    # A 0.1 km / 1 min trip should still return at least the minimum fare
    fare = calculate_fare("ECONOMY", 0.1, 60, 1.0)
    assert fare >= TIER_RATES["ECONOMY"]["min_fare"]


def test_calculate_fare_surge_multiplier():
    base_fare = calculate_fare("ECONOMY", 5.0, 600, 1.0)
    surged_fare = calculate_fare("ECONOMY", 5.0, 600, 2.0)
    assert surged_fare == pytest.approx(base_fare * 2, rel=1e-3)


def test_calculate_fare_tiers_ascending():
    kwargs = dict(distance_km=5.0, duration_sec=600, surge_multiplier=1.0)
    economy = calculate_fare("ECONOMY", **kwargs)
    premium = calculate_fare("PREMIUM", **kwargs)
    luxury = calculate_fare("LUXURY", **kwargs)
    assert economy < premium < luxury


def test_calculate_fare_surge_capped_externally():
    # calculate_fare itself doesn't cap surge; the cap is applied in get_surge_multiplier
    fare = calculate_fare("ECONOMY", 5.0, 600, 3.0)
    assert fare > 0
