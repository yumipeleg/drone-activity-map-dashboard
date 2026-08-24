"""Focused API tests for GET /api/drones/{drone_id}/history.

Isolation: see tests/conftest.py.
"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.drone_telemetry import DroneTelemetry
from app.models.enums import DroneStatus

client = TestClient(app)


def _seed(**overrides) -> DroneTelemetry:
    defaults = dict(
        drone_id="DRONE-001",
        drone_type="Quadcopter",
        operator_id="OP-123",
        latitude=32.0,
        longitude=34.0,
        altitude_m=100.0,
        speed_kmh=40.0,
        battery_percent=80,
        timestamp=datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc),
        status=DroneStatus.ACTIVE,
    )
    defaults.update(overrides)

    with SessionLocal() as db:
        record = DroneTelemetry(**defaults)
        db.add(record)
        db.commit()
        db.refresh(record)
        return record


def test_history_returns_rows_oldest_to_newest() -> None:
    _seed(drone_id="DRONE-001", timestamp=datetime(2026, 6, 28, 10, 10, tzinfo=timezone.utc), latitude=3.0)
    _seed(drone_id="DRONE-001", timestamp=datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc), latitude=1.0)
    _seed(drone_id="DRONE-001", timestamp=datetime(2026, 6, 28, 10, 5, tzinfo=timezone.utc), latitude=2.0)

    response = client.get("/api/drones/DRONE-001/history")

    assert response.status_code == 200
    body = response.json()
    assert [item["latitude"] for item in body] == [1.0, 2.0, 3.0]


def test_history_only_returns_the_requested_business_drone_id() -> None:
    _seed(drone_id="DRONE-001", timestamp=datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc))
    _seed(drone_id="DRONE-002", timestamp=datetime(2026, 6, 28, 10, 5, tzinfo=timezone.utc))

    response = client.get("/api/drones/DRONE-001/history")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["drone_id"] == "DRONE-001"


def test_history_for_unknown_drone_returns_200_and_empty_list() -> None:
    response = client.get("/api/drones/DOES-NOT-EXIST/history")

    assert response.status_code == 200
    assert response.json() == []


def test_history_is_not_a_paginated_envelope() -> None:
    _seed(drone_id="DRONE-001")

    response = client.get("/api/drones/DRONE-001/history")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
