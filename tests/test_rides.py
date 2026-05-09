from __future__ import annotations

"""Integration tests for POST /v1/rides and GET /v1/rides/{id}."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_ride_validation_error(client: AsyncClient):
    """Missing required fields should return 422."""
    resp = await client.post("/v1/rides", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_ride_invalid_tier(client: AsyncClient, sample_rider_id):
    resp = await client.post(
        "/v1/rides",
        json={
            "rider_id": str(sample_rider_id),
            "pickup_lat": 12.97,
            "pickup_lng": 77.59,
            "destination_lat": 12.98,
            "destination_lng": 77.60,
            "tier": "HELICOPTER",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_ride_not_found(client: AsyncClient):
    resp = await client.get(f"/v1/rides/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
@patch("app.api.v1.rides.run_matching", new_callable=AsyncMock)
@patch("app.api.v1.rides.estimate_fare", new_callable=AsyncMock)
async def test_create_ride_success(mock_fare, mock_match, client: AsyncClient, session, sample_rider_id):
    """A valid ride request should be created with PENDING status."""
    from app.models.rider import Rider
    import secrets

    # Seed a rider
    rider = Rider(
        id=sample_rider_id,
        name="Test Rider",
        phone="+91" + str(uuid.uuid4().int)[:10],
        email=f"rider_{uuid.uuid4().hex[:8]}@test.com",
        api_key=secrets.token_hex(16),
    )
    session.add(rider)
    await session.commit()

    mock_fare.return_value = (120.0, 1.0)
    mock_match.return_value = None  # fire-and-forget, don't actually run

    resp = await client.post(
        "/v1/rides",
        json={
            "rider_id": str(sample_rider_id),
            "pickup_lat": 12.9716,
            "pickup_lng": 77.5946,
            "destination_lat": 12.9352,
            "destination_lng": 77.6245,
            "tier": "ECONOMY",
            "payment_method": "CASH",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "PENDING"
    assert data["estimated_fare"] == 120.0
    assert data["tier"] == "ECONOMY"
    assert uuid.UUID(data["id"])


@pytest.mark.asyncio
@patch("app.api.v1.rides.run_matching", new_callable=AsyncMock)
@patch("app.api.v1.rides.estimate_fare", new_callable=AsyncMock)
async def test_idempotency_key_deduplicates(mock_fare, mock_match, client: AsyncClient, session):
    """Two requests with the same Idempotency-Key should return the same ride."""
    from app.models.rider import Rider
    import secrets

    rider_id = uuid.uuid4()
    rider = Rider(
        id=rider_id,
        name="Idem Rider",
        phone="+91" + str(uuid.uuid4().int)[:10],
        email=f"idem_{uuid.uuid4().hex[:8]}@test.com",
        api_key=secrets.token_hex(16),
    )
    session.add(rider)
    await session.commit()

    mock_fare.return_value = (80.0, 1.0)
    mock_match.return_value = None

    payload = {
        "rider_id": str(rider_id),
        "pickup_lat": 12.97,
        "pickup_lng": 77.59,
        "destination_lat": 12.98,
        "destination_lng": 77.60,
        "tier": "ECONOMY",
    }
    idem_key = f"test-{uuid.uuid4()}"
    headers = {"Idempotency-Key": idem_key}

    r1 = await client.post("/v1/rides", json=payload, headers=headers)
    r2 = await client.post("/v1/rides", json=payload, headers=headers)

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]
