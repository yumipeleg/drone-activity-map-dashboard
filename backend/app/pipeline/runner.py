"""Pipeline runner — orchestrates load -> normalize/validate -> detect
duplicates -> persist -> update PipelineRun status.

This module must never import FastAPI or Celery: the exact same
`run_pipeline()` is meant to be called from an API route today and from a
Celery task later, with zero rewriting. See AGENTS.md.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import SessionLocal
from app.models.drone_telemetry import DroneTelemetry
from app.models.enums import PipelineRunStatus
from app.models.pipeline_run import PipelineRun
from app.pipeline.loader import load_raw_records
from app.schemas.drone_telemetry import DroneTelemetryInput


@dataclass(frozen=True)
class PipelineResult:
    """Plain summary of a finished pipeline run.

    Returned instead of the raw `PipelineRun` ORM object: by the time the
    caller sees this, the runner's own session has already been closed, so
    reading attributes directly off the ORM object could raise a
    DetachedInstanceError.
    """

    pipeline_run_id: int
    status: PipelineRunStatus
    total_records: int
    valid_records: int
    invalid_records: int
    duplicate_records: int
    error_message: str | None


def run_pipeline(input_path: str | Path | None = None) -> PipelineResult:
    """Run the ingestion pipeline once and return a summary of the result.

    Never raises on a "normal" failure (a bad input file, a bad record, a
    duplicate, or an unexpected DB error) — those are all captured in the
    returned `PipelineResult.status` / `error_message`, with the
    `PipelineRun` history row updated to match. A Celery task added later
    can inspect the returned status and decide for itself whether a
    "failed" result should also raise a task-level exception; that
    decision is deliberately kept out of this function.
    """
    path = Path(input_path) if input_path is not None else Path(settings.pipeline_input_file)

    db = SessionLocal()
    run = PipelineRun(status=PipelineRunStatus.STARTED, started_at=_utc_now())
    db.add(run)
    db.commit()
    pipeline_run_id = run.id

    total = valid = invalid = duplicate = 0
    status = PipelineRunStatus.COMPLETED
    error_message: str | None = None

    try:
        raw_records = load_raw_records(path)
        total = len(raw_records)

        validated_records: list[DroneTelemetryInput] = []
        for raw_record in raw_records:
            try:
                validated_records.append(DroneTelemetryInput.model_validate(raw_record))
            except ValidationError:
                invalid += 1

        existing_pairs = _load_existing_pairs(db, validated_records)

        for record in validated_records:
            pair = (record.drone_id, record.timestamp)
            if pair in existing_pairs:
                duplicate += 1
                continue

            db.add(DroneTelemetry(**record.model_dump()))
            try:
                db.commit()
            except IntegrityError:
                # Belated safety net: the DB unique constraint is the final
                # guarantee even if the pre-check above ever misses a case
                # (e.g. a concurrent run inserting the same pair).
                db.rollback()
                duplicate += 1
                continue

            existing_pairs.add(pair)
            valid += 1

    except Exception as exc:  # noqa: BLE001 - anything else is fatal to the run
        db.rollback()
        status = PipelineRunStatus.FAILED
        error_message = str(exc)

    _finalize_run(db, run, status, total, valid, invalid, duplicate, error_message)
    db.close()

    return PipelineResult(
        pipeline_run_id=pipeline_run_id,
        status=status,
        total_records=total,
        valid_records=valid,
        invalid_records=invalid,
        duplicate_records=duplicate,
        error_message=error_message,
    )


def _finalize_run(
    db: Session,
    run: PipelineRun,
    status: PipelineRunStatus,
    total: int,
    valid: int,
    invalid: int,
    duplicate: int,
    error_message: str | None,
) -> None:
    run.status = status
    run.finished_at = _utc_now()
    run.total_records = total
    run.valid_records = valid
    run.invalid_records = invalid
    run.duplicate_records = duplicate
    run.error_message = error_message
    db.commit()


def _load_existing_pairs(
    db: Session, validated_records: list[DroneTelemetryInput]
) -> set[tuple[str, datetime]]:
    """One batched query for exactly the (drone_id, timestamp) pairs present
    in this validated batch — not each drone's full history — so duplicate
    detection stays cheap no matter how much data already exists.
    """
    candidate_pairs = [(record.drone_id, record.timestamp) for record in validated_records]
    if not candidate_pairs:
        return set()

    rows = (
        db.query(DroneTelemetry.drone_id, DroneTelemetry.timestamp)
        .filter(tuple_(DroneTelemetry.drone_id, DroneTelemetry.timestamp).in_(candidate_pairs))
        .all()
    )
    return {(drone_id, ts) for drone_id, ts in rows}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
