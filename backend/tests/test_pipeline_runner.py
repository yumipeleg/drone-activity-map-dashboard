"""Focused integration tests for the pipeline runner against the dedicated
test database.

Test isolation strategy: `run_pipeline()` owns its own DB session and
commits per record (see app/pipeline/runner.py), so a per-test transaction
rollback would not actually undo anything it persists. Instead, the shared
`clean_pipeline_tables` fixture in tests/conftest.py wipes the
`drone_telemetry` and `pipeline_run` tables before and after every test —
see that file for how the dedicated "drone_activity_test" database is
selected and prepared, which is what makes this safe to do unconditionally.
"""

import json
from pathlib import Path

import pytest

from app.db.session import SessionLocal
from app.models.drone_telemetry import DroneTelemetry
from app.models.enums import PipelineRunStatus
from app.models.pipeline_run import PipelineRun
from app.pipeline.runner import create_pipeline_run, execute_pipeline_run, run_pipeline

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

INVALID_RECORD = {
    "drone_id": "",
    "drone_type": "Quadcopter",
    "operator_id": "OP-123",
    "latitude": 200,
    "longitude": 34.7818,
    "altitude_m": -50,
    "battery_percent": 150,
    "timestamp": "invalid-date",
    "status": "flying",
}


def _write_input(tmp_path: Path, records: list[dict]) -> Path:
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(records), encoding="utf-8")
    return input_path


def test_mixed_valid_and_invalid_input(tmp_path: Path) -> None:
    input_path = _write_input(tmp_path, [VALID_RECORD, INVALID_RECORD])

    result = run_pipeline(input_path)

    assert result.status == PipelineRunStatus.COMPLETED
    assert result.total_records == 2
    assert result.valid_records == 1
    assert result.invalid_records == 1
    assert result.duplicate_records == 0

    with SessionLocal() as db:
        assert db.query(DroneTelemetry).count() == 1


def test_duplicate_within_same_file_is_skipped(tmp_path: Path) -> None:
    input_path = _write_input(tmp_path, [VALID_RECORD, dict(VALID_RECORD)])

    result = run_pipeline(input_path)

    assert result.status == PipelineRunStatus.COMPLETED
    assert result.valid_records == 1
    assert result.duplicate_records == 1
    assert result.invalid_records == 0

    with SessionLocal() as db:
        assert db.query(DroneTelemetry).count() == 1


def test_duplicate_against_existing_row_is_skipped(tmp_path: Path) -> None:
    input_path = _write_input(tmp_path, [VALID_RECORD])
    run_pipeline(input_path)  # first run persists the record

    result = run_pipeline(input_path)  # second run should find it a duplicate

    assert result.status == PipelineRunStatus.COMPLETED
    assert result.valid_records == 0
    assert result.duplicate_records == 1

    with SessionLocal() as db:
        assert db.query(DroneTelemetry).count() == 1


def test_fatal_load_failure_marks_run_failed(tmp_path: Path) -> None:
    missing_path = tmp_path / "does-not-exist.json"

    result = run_pipeline(missing_path)

    assert result.status == PipelineRunStatus.FAILED
    assert result.error_message is not None
    assert result.total_records == 0


def test_pipeline_run_counters_are_consistent(tmp_path: Path) -> None:
    input_path = _write_input(tmp_path, [VALID_RECORD, INVALID_RECORD])

    result = run_pipeline(input_path)

    assert result.total_records == (
        result.valid_records + result.invalid_records + result.duplicate_records
    )

    with SessionLocal() as db:
        run = db.get(PipelineRun, result.pipeline_run_id)
        assert run is not None
        assert run.status == PipelineRunStatus.COMPLETED


# --- create_pipeline_run / execute_pipeline_run (Celery-ready split) --------


def test_create_pipeline_run_creates_exactly_one_queued_row() -> None:
    with SessionLocal() as db:
        run = create_pipeline_run(db)

        assert run.id is not None
        assert run.status == PipelineRunStatus.QUEUED
        assert run.started_at is not None
        assert run.finished_at is None

    with SessionLocal() as db:
        assert db.query(PipelineRun).count() == 1
        persisted = db.get(PipelineRun, run.id)
        assert persisted is not None
        assert persisted.status == PipelineRunStatus.QUEUED


def test_execute_pipeline_run_executes_and_finalizes_an_existing_row(tmp_path: Path) -> None:
    input_path = _write_input(tmp_path, [VALID_RECORD, INVALID_RECORD])

    with SessionLocal() as db:
        created = create_pipeline_run(db)
        run_id = created.id

    result = execute_pipeline_run(run_id, input_path)

    assert result.pipeline_run_id == run_id
    assert result.status == PipelineRunStatus.COMPLETED
    assert result.total_records == 2
    assert result.valid_records == 1
    assert result.invalid_records == 1
    assert result.duplicate_records == 0

    with SessionLocal() as db:
        assert db.query(DroneTelemetry).count() == 1
        run = db.get(PipelineRun, run_id)
        assert run is not None
        assert run.status == PipelineRunStatus.COMPLETED
        assert run.finished_at is not None


def test_execute_pipeline_run_does_not_create_another_pipeline_run(tmp_path: Path) -> None:
    input_path = _write_input(tmp_path, [VALID_RECORD])

    with SessionLocal() as db:
        created = create_pipeline_run(db)
        run_id = created.id

    execute_pipeline_run(run_id, input_path)

    with SessionLocal() as db:
        assert db.query(PipelineRun).count() == 1


def test_execute_pipeline_run_raises_value_error_for_nonexistent_run_id(tmp_path: Path) -> None:
    input_path = _write_input(tmp_path, [VALID_RECORD])
    nonexistent_run_id = 999_999

    with pytest.raises(ValueError, match=str(nonexistent_run_id)):
        execute_pipeline_run(nonexistent_run_id, input_path)

    with SessionLocal() as db:
        assert db.query(PipelineRun).count() == 0
        assert db.query(DroneTelemetry).count() == 0


def test_execute_pipeline_run_rejects_terminal_completed_run_without_modifying_it(
    tmp_path: Path,
) -> None:
    input_path = _write_input(tmp_path, [VALID_RECORD])

    with SessionLocal() as db:
        created = create_pipeline_run(db)
        run_id = created.id

    execute_pipeline_run(run_id, input_path)

    with pytest.raises(ValueError, match="terminal status completed"):
        execute_pipeline_run(run_id, input_path)

    with SessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        assert run is not None
        assert run.status == PipelineRunStatus.COMPLETED
        assert db.query(PipelineRun).count() == 1


def test_execute_pipeline_run_rejects_terminal_failed_run_without_modifying_it(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "does-not-exist.json"

    with SessionLocal() as db:
        created = create_pipeline_run(db)
        run_id = created.id

    execute_pipeline_run(run_id, missing_path)

    with pytest.raises(ValueError, match="terminal status failed"):
        execute_pipeline_run(run_id, missing_path)

    with SessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        assert run is not None
        assert run.status == PipelineRunStatus.FAILED
        assert db.query(PipelineRun).count() == 1


def test_run_pipeline_remains_backward_compatible_and_creates_exactly_one_run(
    tmp_path: Path,
) -> None:
    input_path = _write_input(tmp_path, [VALID_RECORD])

    result = run_pipeline(input_path)

    assert result.status == PipelineRunStatus.COMPLETED
    assert result.valid_records == 1

    with SessionLocal() as db:
        assert db.query(PipelineRun).count() == 1
        run = db.get(PipelineRun, result.pipeline_run_id)
        assert run is not None
        assert run.status == PipelineRunStatus.COMPLETED
