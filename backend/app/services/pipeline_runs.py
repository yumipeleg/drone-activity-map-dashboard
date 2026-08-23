"""Read-only query operations for `PipelineRun` history.

Kept as plain functions rather than a class: there is no shared state, and
each route just needs `db` + a couple of parameters (route -> service ->
SQLAlchemy, per ARCHITECTURE.md).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pipeline_run import PipelineRun


def list_pipeline_runs(db: Session, limit: int) -> list[PipelineRun]:
    """Most recent runs first, capped at `limit`."""
    statement = select(PipelineRun).order_by(PipelineRun.id.desc()).limit(limit)
    return list(db.execute(statement).scalars().all())


def get_pipeline_run(db: Session, run_id: int) -> PipelineRun | None:
    return db.get(PipelineRun, run_id)
