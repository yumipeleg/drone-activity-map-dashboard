"""Routes for triggering and inspecting pipeline runs.

`POST /api/pipeline/run` creates a `QUEUED` row and enqueues a Celery task;
processing happens asynchronously in a worker via `execute_pipeline_run`.
The `GET` routes delegate all querying to app/services/pipeline_runs.py.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from kombu.exceptions import OperationalError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.enums import PipelineRunStatus
from app.pipeline.runner import create_pipeline_run
from app.schemas.pipeline_run import PipelineRunRead
from app.services import pipeline_runs as pipeline_runs_service
from app.tasks import run_pipeline_task

router = APIRouter(tags=["pipeline"])


@router.post("/api/pipeline/run", response_model=PipelineRunRead, status_code=202)
def trigger_pipeline_run(db: Session = Depends(get_db)) -> PipelineRunRead | JSONResponse:
    """Accept a new pipeline run for background processing.

    Creates a `QUEUED` `PipelineRun` row, enqueues `run_pipeline_task` with
    its id, and returns immediately with HTTP 202. The worker transitions the
    run through `STARTED` to `COMPLETED` or `FAILED`; poll
    `GET /api/pipeline/runs/{id}` for the final state.

    If the broker is unavailable, the same row is marked `FAILED` with an
    enqueue error message and HTTP 503 is returned.
    """
    run = create_pipeline_run(db)

    try:
        run_pipeline_task.delay(run.id)
    except OperationalError as exc:
        run.status = PipelineRunStatus.FAILED
        run.finished_at = datetime.now(timezone.utc)
        run.error_message = f"Failed to enqueue pipeline run: {exc}"
        db.commit()
        return JSONResponse(
            status_code=503,
            content=PipelineRunRead.model_validate(run).model_dump(mode="json"),
        )

    return PipelineRunRead.model_validate(run)


@router.get("/api/pipeline/runs", response_model=list[PipelineRunRead])
def list_pipeline_runs(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[PipelineRunRead]:
    """Recent run history, most recent first."""
    runs = pipeline_runs_service.list_pipeline_runs(db, limit=limit)
    return [PipelineRunRead.model_validate(run) for run in runs]


@router.get("/api/pipeline/runs/{run_id}", response_model=PipelineRunRead)
def get_pipeline_run(run_id: int, db: Session = Depends(get_db)) -> PipelineRunRead:
    run = pipeline_runs_service.get_pipeline_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")
    return PipelineRunRead.model_validate(run)
