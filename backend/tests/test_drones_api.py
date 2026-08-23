"""Focused API tests for the drone telemetry query endpoints.

Isolation: see tests/conftest.py for the dedicated test database and the
shared `clean_pipeline_tables` fixture applied around every test. Records
here are seeded directly through the ORM (not through the pipeline) since
these tests are only about filtering/lookup behavior.
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


def test_list_drones_no_filters_returns_all_records() -> None:
    _seed(drone_id="DRONE-001")
    _seed(drone_id="DRONE-002", timestamp=datetime(2026, 6, 28, 10, 5, tzinfo=timezone.utc))

    response = client.get("/api/drones")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_filter_by_drone_type() -> None:
    _seed(drone_type="Quadcopter")
    _seed(drone_type="Fixed Wing", timestamp=datetime(2026, 6, 28, 10, 5, tzinfo=timezone.utc))

    response = client.get("/api/drones", params={"drone_type": "Fixed Wing"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["drone_type"] == "Fixed Wing"


def test_filter_by_status() -> None:
    _seed(status=DroneStatus.ACTIVE)
    _seed(status=DroneStatus.LOST_SIGNAL, timestamp=datetime(2026, 6, 28, 10, 5, tzinfo=timezone.utc))

    response = client.get("/api/drones", params={"status": "lost_signal"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["status"] == "lost_signal"


def test_filter_by_operator_id() -> None:
    _seed(operator_id="OP-123")
    _seed(operator_id="OP-456", timestamp=datetime(2026, 6, 28, 10, 5, tzinfo=timezone.utc))

    response = client.get("/api/drones", params={"operator_id": "OP-456"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["operator_id"] == "OP-456"


def test_filter_by_min_battery() -> None:
    _seed(battery_percent=15)
    _seed(battery_percent=80, timestamp=datetime(2026, 6, 28, 10, 5, tzinfo=timezone.utc))

    response = client.get("/api/drones", params={"min_battery": 50})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["battery_percent"] == 80


def test_filter_by_date_range_is_inclusive_of_the_to_date() -> None:
    _seed(timestamp=datetime(2026, 6, 27, 23, 0, tzinfo=timezone.utc))  # before range
    _seed(timestamp=datetime(2026, 6, 28, 12, 0, tzinfo=timezone.utc))  # inside range
    _seed(timestamp=datetime(2026, 6, 29, 1, 0, tzinfo=timezone.utc))  # inside range ("to" day)
    _seed(timestamp=datetime(2026, 6, 30, 0, 0, tzinfo=timezone.utc))  # after range

    response = client.get("/api/drones", params={"from": "2026-06-28", "to": "2026-06-29"})

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_combined_filters() -> None:
    _seed(drone_type="Quadcopter", status=DroneStatus.ACTIVE, battery_percent=80)
    _seed(
        drone_type="Quadcopter",
        status=DroneStatus.LOST_SIGNAL,
        battery_percent=10,
        timestamp=datetime(2026, 6, 28, 10, 5, tzinfo=timezone.utc),
    )
    _seed(
        drone_type="Fixed Wing",
        status=DroneStatus.ACTIVE,
        battery_percent=80,
        timestamp=datetime(2026, 6, 28, 10, 10, tzinfo=timezone.utc),
    )

    response = client.get("/api/drones", params={"drone_type": "Quadcopter", "status": "active"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["drone_type"] == "Quadcopter"
    assert body[0]["status"] == "active"


def test_invalid_status_filter_returns_422() -> None:
    response = client.get("/api/drones", params={"status": "flying"})

    assert response.status_code == 422


def test_invalid_min_battery_returns_422() -> None:
    response = client.get("/api/drones", params={"min_battery": 150})

    assert response.status_code == 422


def test_get_drone_found() -> None:
    seeded = _seed()

    response = client.get(f"/api/drones/{seeded.id}")

    assert response.status_code == 200
    assert response.json()["id"] == seeded.id


def test_get_drone_not_found() -> None:
    response = client.get("/api/drones/999999")

    assert response.status_code == 404


def test_get_drone_non_integer_id_returns_422() -> None:
    response = client.get("/api/drones/not-a-number")

    assert response.status_code == 422
