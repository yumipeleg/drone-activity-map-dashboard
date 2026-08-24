"""Focused API tests for the drone telemetry query endpoints.

Isolation: see tests/conftest.py for the dedicated test database and the
shared `clean_pipeline_tables` fixture applied around every test. Records
here are seeded directly through the ORM (not through the pipeline) since
these tests are only about filtering/lookup/pagination behavior.
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
    body = response.json()
    assert len(body["items"]) == 2
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["page_size"] == 20


def test_filter_by_drone_type() -> None:
    _seed(drone_type="Quadcopter")
    _seed(drone_type="Fixed Wing", timestamp=datetime(2026, 6, 28, 10, 5, tzinfo=timezone.utc))

    response = client.get("/api/drones", params={"drone_type": "Fixed Wing"})

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["drone_type"] == "Fixed Wing"


def test_filter_by_status() -> None:
    _seed(status=DroneStatus.ACTIVE)
    _seed(status=DroneStatus.LOST_SIGNAL, timestamp=datetime(2026, 6, 28, 10, 5, tzinfo=timezone.utc))

    response = client.get("/api/drones", params={"status": "lost_signal"})

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "lost_signal"


def test_filter_by_operator_id() -> None:
    _seed(operator_id="OP-123")
    _seed(operator_id="OP-456", timestamp=datetime(2026, 6, 28, 10, 5, tzinfo=timezone.utc))

    response = client.get("/api/drones", params={"operator_id": "OP-456"})

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["operator_id"] == "OP-456"


def test_filter_by_min_battery() -> None:
    _seed(battery_percent=15)
    _seed(battery_percent=80, timestamp=datetime(2026, 6, 28, 10, 5, tzinfo=timezone.utc))

    response = client.get("/api/drones", params={"min_battery": 50})

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["battery_percent"] == 80


def test_filter_by_date_range_is_inclusive_of_the_to_date() -> None:
    _seed(timestamp=datetime(2026, 6, 27, 23, 0, tzinfo=timezone.utc))  # before range
    _seed(timestamp=datetime(2026, 6, 28, 12, 0, tzinfo=timezone.utc))  # inside range
    _seed(timestamp=datetime(2026, 6, 29, 1, 0, tzinfo=timezone.utc))  # inside range ("to" day)
    _seed(timestamp=datetime(2026, 6, 30, 0, 0, tzinfo=timezone.utc))  # after range

    response = client.get("/api/drones", params={"from": "2026-06-28", "to": "2026-06-29"})

    assert response.status_code == 200
    assert len(response.json()["items"]) == 2


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
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["drone_type"] == "Quadcopter"
    assert items[0]["status"] == "active"


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


# --- latest_only ------------------------------------------------------------


def test_latest_only_returns_one_row_per_drone_with_the_greatest_timestamp() -> None:
    _seed(drone_id="DRONE-001", timestamp=datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc), latitude=1.0)
    _seed(drone_id="DRONE-001", timestamp=datetime(2026, 6, 28, 10, 10, tzinfo=timezone.utc), latitude=3.0)
    _seed(drone_id="DRONE-001", timestamp=datetime(2026, 6, 28, 10, 5, tzinfo=timezone.utc), latitude=2.0)
    _seed(drone_id="DRONE-002", timestamp=datetime(2026, 6, 28, 9, 0, tzinfo=timezone.utc), latitude=9.0)

    response = client.get("/api/drones", params={"latest_only": "true"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    by_drone = {item["drone_id"]: item for item in body["items"]}
    assert by_drone["DRONE-001"]["latitude"] == 3.0  # 10:10 row, not the earlier 10:00/10:05 rows
    assert by_drone["DRONE-002"]["latitude"] == 9.0


def test_latest_only_status_filter_applies_after_latest_selection_not_before() -> None:
    # DRONE-001 was lost_signal at 10:00 but is active now (10:10) — a
    # status=lost_signal filter must NOT resurrect the earlier row.
    _seed(drone_id="DRONE-001", status=DroneStatus.LOST_SIGNAL, timestamp=datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc))
    _seed(drone_id="DRONE-001", status=DroneStatus.ACTIVE, timestamp=datetime(2026, 6, 28, 10, 10, tzinfo=timezone.utc))

    response = client.get("/api/drones", params={"latest_only": "true", "status": "lost_signal"})

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_latest_only_min_battery_filter_applies_after_latest_selection() -> None:
    # DRONE-001 had 80% battery at 10:00 but is down to 10% now (10:10) — a
    # min_battery=50 filter must exclude it based on the CURRENT reading.
    _seed(drone_id="DRONE-001", battery_percent=80, timestamp=datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc))
    _seed(drone_id="DRONE-001", battery_percent=10, timestamp=datetime(2026, 6, 28, 10, 10, tzinfo=timezone.utc))

    response = client.get("/api/drones", params={"latest_only": "true", "min_battery": 50})

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_latest_only_date_range_applies_to_the_absolute_latest_row() -> None:
    # DRONE-001's absolute latest report is in July, outside the requested
    # June range — it must not reappear via its earlier June row.
    _seed(drone_id="DRONE-001", timestamp=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc))
    _seed(drone_id="DRONE-001", timestamp=datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc))

    response = client.get("/api/drones", params={"latest_only": "true", "from": "2026-06-01", "to": "2026-06-30"})

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_latest_only_ignores_page_size_and_returns_every_matching_drone() -> None:
    for i in range(5):
        _seed(drone_id=f"DRONE-{i:03d}", timestamp=datetime(2026, 6, 28, 10, i, tzinfo=timezone.utc))

    response = client.get("/api/drones", params={"latest_only": "true", "page": 1, "page_size": 2})

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 5
    assert body["total"] == 5
    assert body["page"] == 1
    assert body["page_size"] == 5


# --- pagination (latest_only=false) -----------------------------------------


def test_pagination_defaults_to_page_1_size_20() -> None:
    for i in range(3):
        _seed(drone_id="DRONE-001", timestamp=datetime(2026, 6, 28, 10, i, tzinfo=timezone.utc))

    response = client.get("/api/drones")

    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total"] == 3
    assert len(body["items"]) == 3


def test_pagination_explicit_page_and_page_size_returns_correct_slice() -> None:
    for i in range(5):
        _seed(drone_id="DRONE-001", timestamp=datetime(2026, 6, 28, 10, i, tzinfo=timezone.utc))

    response = client.get("/api/drones", params={"page": 2, "page_size": 2})

    body = response.json()
    assert response.status_code == 200
    assert body["total"] == 5
    assert body["page"] == 2
    assert body["page_size"] == 2
    assert len(body["items"]) == 2
    # Ordered newest-first: page 1 = minutes [4, 3], page 2 = [2, 1].
    assert [item["timestamp"][:16] for item in body["items"]] == ["2026-06-28T10:02", "2026-06-28T10:01"]


def test_pagination_empty_page_returns_no_items_but_correct_total() -> None:
    _seed(drone_id="DRONE-001")

    response = client.get("/api/drones", params={"page": 5, "page_size": 20})

    body = response.json()
    assert response.status_code == 200
    assert body["items"] == []
    assert body["total"] == 1


def test_pagination_page_size_over_100_returns_422() -> None:
    response = client.get("/api/drones", params={"page_size": 101})

    assert response.status_code == 422


def test_pagination_page_below_1_returns_422() -> None:
    response = client.get("/api/drones", params={"page": 0})

    assert response.status_code == 422


def test_pagination_combined_with_filters() -> None:
    for i in range(3):
        _seed(drone_type="Quadcopter", timestamp=datetime(2026, 6, 28, 10, i, tzinfo=timezone.utc))
    _seed(drone_type="Fixed Wing", timestamp=datetime(2026, 6, 28, 10, 10, tzinfo=timezone.utc))

    response = client.get("/api/drones", params={"drone_type": "Quadcopter", "page": 1, "page_size": 2})

    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert all(item["drone_type"] == "Quadcopter" for item in body["items"])
