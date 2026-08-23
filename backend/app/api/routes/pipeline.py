"""Routes for triggering and inspecting pipeline runs.

Thin by design: `POST /api/pipeline/run` calls the framework-independent
`run_pipeline()` directly (no pipeline logic here — see AGENTS.md); the
`GET` routes delegate all querying to app/services/pipeline_runs.py.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.pipeline.runner import run_pipeline
from app.schemas.pipeline_run import PipelineRunRead
from app.services import pipeline_runs as pipeline_runs_service

router = APIRouter(tags=["pipeline"])


@router.post("/api/pipeline/run", response_model=PipelineRunRead)
def trigger_pipeline_run(db: Session = Depends(get_db)) -> PipelineRunRead:
    """Run the ingestion pipeline synchronously and return its final state.

    `run_pipeline()` returns a `PipelineResult`, not the `PipelineRun` ORM
    row (its own DB session is already closed by the time it returns — see
    runner.py). Rather than adding a second, slightly different response
    schema just for this endpoint, this route re-fetches the same row by
    `pipeline_run_id` and returns it as a `PipelineRunRead` — the exact same
    schema `GET /api/pipeline/runs` and `GET /api/pipeline/runs/{id}` use.
    That keeps "a pipeline run" a single, consistent API shape everywhere,
    at the cost of one extra cheap by-PK lookup here.

    Always returns HTTP 200, even when the run's own domain status ends up
    "failed" (see `PipelineRunRead.status`) — that is a normal, fully
    persisted outcome, not an HTTP-level error. An infrastructure failure
    severe enough that `run_pipeline()` could not even create a
    `PipelineRun` row is a real, unhandled exception, which FastAPI turns
    into an actual HTTP 500 by default.
    """
    result = run_pipeline()

    run = pipeline_runs_service.get_pipeline_run(db, result.pipeline_run_id)
    if run is None:
        # Defensive only: run_pipeline() always creates its PipelineRun row
        # before doing anything else, so this should be unreachable.
        raise HTTPException(status_code=500, detail="Pipeline run result could not be retrieved")

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
