"""Focused API tests for GET /api/stats.

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


def test_stats_with_no_data_returns_zeros_and_null_average() -> None:
    response = client.get("/api/stats")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "total_telemetry_records": 0,
        "distinct_drones": 0,
        "active_drones": 0,
        "landed_drones": 0,
        "lost_signal_drones": 0,
        "low_battery_drones": 0,
        "average_battery_percent": None,
    }


def test_total_telemetry_records_counts_every_historical_row() -> None:
    _seed(drone_id="DRONE-001", timestamp=datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc))
    _seed(drone_id="DRONE-001", timestamp=datetime(2026, 6, 28, 10, 5, tzinfo=timezone.utc))
    _seed(drone_id="DRONE-002", timestamp=datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc))

    response = client.get("/api/stats")

    body = response.json()
    assert body["total_telemetry_records"] == 3
    assert body["distinct_drones"] == 2


def test_current_state_counts_reflect_latest_row_not_history() -> None:
    # DRONE-001 was lost_signal at 10:00 but is active now (10:10) — it must
    # count only as active, not lost_signal.
    _seed(drone_id="DRONE-001", status=DroneStatus.LOST_SIGNAL, timestamp=datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc))
    _seed(drone_id="DRONE-001", status=DroneStatus.ACTIVE, timestamp=datetime(2026, 6, 28, 10, 10, tzinfo=timezone.utc))
    _seed(drone_id="DRONE-002", status=DroneStatus.LANDED, timestamp=datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc))
    _seed(drone_id="DRONE-003", status=DroneStatus.LOST_SIGNAL, timestamp=datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc))

    response = client.get("/api/stats")

    body = response.json()
    assert body["active_drones"] == 1
    assert body["landed_drones"] == 1
    assert body["lost_signal_drones"] == 1


def test_low_battery_threshold_is_strictly_below_20() -> None:
    _seed(drone_id="DRONE-001", battery_percent=19, timestamp=datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc))
    _seed(drone_id="DRONE-002", battery_percent=20, timestamp=datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc))

    response = client.get("/api/stats")

    body = response.json()
    assert body["low_battery_drones"] == 1


def test_low_battery_uses_latest_row_only() -> None:
    # DRONE-001 was low battery at 10:00 but has since been "recharged" (a
    # later, higher reading at 10:10) — it must not count as low battery now.
    _seed(drone_id="DRONE-001", battery_percent=5, timestamp=datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc))
    _seed(drone_id="DRONE-001", battery_percent=90, timestamp=datetime(2026, 6, 28, 10, 10, tzinfo=timezone.utc))

    response = client.get("/api/stats")

    assert response.json()["low_battery_drones"] == 0


def test_average_battery_percent_is_averaged_over_latest_rows_only() -> None:
    # DRONE-001: latest battery is 100 (ignore its earlier 0 reading).
    _seed(drone_id="DRONE-001", battery_percent=0, timestamp=datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc))
    _seed(drone_id="DRONE-001", battery_percent=100, timestamp=datetime(2026, 6, 28, 10, 10, tzinfo=timezone.utc))
    # DRONE-002: latest (only) battery is 50.
    _seed(drone_id="DRONE-002", battery_percent=50, timestamp=datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc))

    response = client.get("/api/stats")

    # Average of latest rows only: (100 + 50) / 2 = 75, not (0+100+50)/3.
    assert response.json()["average_battery_percent"] == 75.0


def test_stats_are_not_affected_by_query_parameters() -> None:
    _seed(drone_id="DRONE-001", status=DroneStatus.ACTIVE)

    response = client.get("/api/stats", params={"status": "lost_signal", "drone_type": "Fixed Wing"})

    # /api/stats takes no query params at all — extra/unrelated ones are
    # simply ignored by FastAPI, confirming stats are always global.
    assert response.status_code == 200
    assert response.json()["distinct_drones"] == 1
