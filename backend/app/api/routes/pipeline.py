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

from app.config import settings
from app.db.session import get_db
from app.models.enums import PipelineRunStatus
from app.pipeline.input_files import (
    InputFileNotFoundError,
    UnsupportedInputExtensionError,
    UnsafeInputFilenameError,
    list_available_input_files,
    resolve_input_file,
)
from app.pipeline.runner import create_pipeline_run
from app.schemas.pipeline_run import PipelineInputsRead, PipelineRunCreate, PipelineRunRead
from app.services import pipeline_runs as pipeline_runs_service
from app.tasks import run_pipeline_task

router = APIRouter(tags=["pipeline"])


@router.get("/api/pipeline/inputs", response_model=PipelineInputsRead)
def list_pipeline_inputs() -> PipelineInputsRead:
    """List safe, available input files from the runtime input directory."""
    files = list_available_input_files(settings.pipeline_input_dir)
    return PipelineInputsRead(
        files=files,
        default_file=settings.pipeline_default_input_file,
    )


@router.post("/api/pipeline/run", response_model=PipelineRunRead, status_code=202)
def trigger_pipeline_run(
    payload: PipelineRunCreate | None = None,
    db: Session = Depends(get_db),
) -> PipelineRunRead | JSONResponse:
    """Accept a new pipeline run for background processing.

    Creates a `QUEUED` `PipelineRun` row, enqueues `run_pipeline_task` with
    its id, and returns immediately with HTTP 202. The worker transitions the
    run through `STARTED` to `COMPLETED` or `FAILED`; poll
    `GET /api/pipeline/runs/{id}` for the final state.

    If the broker is unavailable, the same row is marked `FAILED` with an
    enqueue error message and HTTP 503 is returned.
    """
    requested_file = payload.input_file if payload is not None else None
    filename = requested_file or settings.pipeline_default_input_file

    try:
        resolve_input_file(settings.pipeline_input_dir, filename)
    except UnsafeInputFilenameError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UnsupportedInputExtensionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InputFileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    run = create_pipeline_run(db, input_file=filename)

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
