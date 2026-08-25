"""Focused API tests for the pipeline endpoints.

Isolation: the shared `clean_pipeline_tables` fixture in tests/conftest.py
wipes the (dedicated test database's) drone_telemetry/pipeline_run tables
around every test automatically — see that file for how the test database
itself is selected and prepared.

POST /api/pipeline/run is asynchronous: tests mock `run_pipeline_task.delay`
at the route import boundary so no live Redis broker is required.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from kombu.exceptions import OperationalError

from app.db.session import SessionLocal
from app.main import app
from app.models.enums import PipelineRunStatus
from app.models.pipeline_run import PipelineRun

client = TestClient(app)

DELAY_PATCH = "app.api.routes.pipeline.run_pipeline_task"


@pytest.fixture
def mock_delay() -> MagicMock:
    with patch(f"{DELAY_PATCH}.delay") as delay_mock:
        yield delay_mock


def test_post_returns_202_with_queued_run(mock_delay: MagicMock) -> None:
    response = client.post("/api/pipeline/run")

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["finished_at"] is None
    assert body["total_records"] == 0
    assert body["valid_records"] == 0
    assert body["invalid_records"] == 0
    assert body["duplicate_records"] == 0
    assert body["error_message"] is None
    assert body["started_at"] is not None
    assert body["id"] is not None

    mock_delay.assert_called_once_with(body["id"])

    with SessionLocal() as db:
        assert db.query(PipelineRun).count() == 1
        persisted = db.get(PipelineRun, body["id"])
        assert persisted is not None
        assert persisted.status == PipelineRunStatus.QUEUED


def test_get_pipeline_run_returns_queued_run_after_post(mock_delay: MagicMock) -> None:
    created = client.post("/api/pipeline/run").json()

    response = client.get(f"/api/pipeline/runs/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["status"] == "queued"
    assert body["finished_at"] is None


def test_list_pipeline_runs_orders_most_recent_first(mock_delay: MagicMock) -> None:
    first = client.post("/api/pipeline/run").json()
    second = client.post("/api/pipeline/run").json()

    response = client.get("/api/pipeline/runs")

    assert response.status_code == 200
    ids = [run["id"] for run in response.json()]
    assert ids.index(second["id"]) < ids.index(first["id"])


def test_post_enqueue_failure_returns_503_and_marks_run_failed(mock_delay: MagicMock) -> None:
    mock_delay.side_effect = OperationalError("Connection refused")

    response = client.post("/api/pipeline/run")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "failed"
    assert body["finished_at"] is not None
    assert body["error_message"] is not None
    assert "Failed to enqueue pipeline run" in body["error_message"]
    assert body["total_records"] == 0
    assert body["valid_records"] == 0
    assert body["invalid_records"] == 0
    assert body["duplicate_records"] == 0

    run_id = body["id"]
    mock_delay.assert_called_once_with(run_id)

    with SessionLocal() as db:
        assert db.query(PipelineRun).count() == 1
        persisted = db.get(PipelineRun, run_id)
        assert persisted is not None
        assert persisted.status == PipelineRunStatus.FAILED
        assert persisted.finished_at is not None
        assert persisted.error_message is not None


def test_get_pipeline_run_not_found() -> None:
    response = client.get("/api/pipeline/runs/999999")

    assert response.status_code == 404
