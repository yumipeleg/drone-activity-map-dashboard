# Framework-independent drone telemetry ingestion pipeline.
# Must never import FastAPI or Celery — see AGENTS.md. `run_pipeline` remains
# the single entry point today's synchronous API route calls. A future
# Celery task will instead call `create_pipeline_run` (to get a run_id to
# enqueue) and `execute_pipeline_run` (to actually process that run_id) —
# both exported here too, unchanged.

from app.pipeline.runner import (  # noqa: F401
    create_pipeline_run,
    execute_pipeline_run,
    run_pipeline,
)
