"""Focused tests for the Celery pipeline task.

The task body is invoked via `.run()` so no live Redis broker is required.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import settings
from app.db.session import SessionLocal
from app.models.enums import PipelineRunStatus
from app.models.pipeline_run import PipelineRun
from app.pipeline.runner import create_pipeline_run
from app.tasks import run_pipeline_task

VALID_RECORD = {
    "drone_id": "DRONE-CELERY-001",
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


def _write_input(tmp_path: Path, records: list[dict]) -> Path:
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(records), encoding="utf-8")
    return input_path


def test_run_pipeline_task_delegates_to_execute_pipeline_run() -> None:
    with patch("app.tasks.execute_pipeline_run") as execute_mock:
        run_pipeline_task.run(42)

    execute_mock.assert_called_once_with(42)


def test_run_pipeline_task_executes_existing_run_without_creating_another(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_path = _write_input(tmp_path, [VALID_RECORD])
    monkeypatch.setattr(settings, "pipeline_input_file", str(input_path))

    with SessionLocal() as db:
        created = create_pipeline_run(db)
        run_id = created.id

    run_pipeline_task.run(run_id)

    with SessionLocal() as db:
        assert db.query(PipelineRun).count() == 1
        run = db.get(PipelineRun, run_id)
        assert run is not None
        assert run.status == PipelineRunStatus.COMPLETED
