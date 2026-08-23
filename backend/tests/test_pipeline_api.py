"""Focused API tests for the pipeline endpoints.

Isolation: the shared `clean_pipeline_tables` fixture in tests/conftest.py
wipes the (dedicated test database's) drone_telemetry/pipeline_run tables
around every test automatically — see that file for how the test database
itself is selected and prepared.
"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)

VALID_RECORD = {
    "drone_id": "DRONE-001",
    "drone_type": "Quadcopter",
    "operator_id": "OP-123",
    "latitude": 32.0853,
    "longitude": 34.7818,
    "altitude_m": 120,
    "speed_kmh": 45,
    "battery_percent": 76,
    "timestamp": "2026-06-28T10:30:00Z",
    "status": "active",
}


def _use_temp_input(tmp_path: Path, monkeypatch, records: list[dict]) -> None:
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(records), encoding="utf-8")
    monkeypatch.setattr(settings, "pipeline_input_file", str(input_path))


def test_successful_pipeline_run(tmp_path: Path, monkeypatch) -> None:
    _use_temp_input(tmp_path, monkeypatch, [VALID_RECORD])

    response = client.post("/api/pipeline/run")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["total_records"] == 1
    assert body["valid_records"] == 1
    assert body["invalid_records"] == 0
    assert body["duplicate_records"] == 0
    assert body["started_at"] is not None
    assert body["finished_at"] is not None
    assert body["error_message"] is None


def test_duplicate_second_run_returns_completed_with_duplicate_counted(
    tmp_path: Path, monkeypatch
) -> None:
    _use_temp_input(tmp_path, monkeypatch, [VALID_RECORD])
    client.post("/api/pipeline/run")

    response = client.post("/api/pipeline/run")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["valid_records"] == 0
    assert body["duplicate_records"] == 1


def test_fatal_pipeline_run_still_returns_http_200_with_failed_status(
    tmp_path: Path, monkeypatch
) -> None:
    missing_path = tmp_path / "does-not-exist.json"
    monkeypatch.setattr(settings, "pipeline_input_file", str(missing_path))

    response = client.post("/api/pipeline/run")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["error_message"] is not None


def test_list_pipeline_runs_orders_most_recent_first(tmp_path: Path, monkeypatch) -> None:
    _use_temp_input(tmp_path, monkeypatch, [VALID_RECORD])
    first = client.post("/api/pipeline/run").json()
    second = client.post("/api/pipeline/run").json()

    response = client.get("/api/pipeline/runs")

    assert response.status_code == 200
    ids = [run["id"] for run in response.json()]
    assert ids.index(second["id"]) < ids.index(first["id"])


def test_get_pipeline_run_found(tmp_path: Path, monkeypatch) -> None:
    _use_temp_input(tmp_path, monkeypatch, [VALID_RECORD])
    created = client.post("/api/pipeline/run").json()

    response = client.get(f"/api/pipeline/runs/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_pipeline_run_not_found() -> None:
    response = client.get("/api/pipeline/runs/999999")

    assert response.status_code == 404
