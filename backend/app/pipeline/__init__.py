# Framework-independent drone telemetry ingestion pipeline.
# Must never import FastAPI or Celery — see AGENTS.md. `run_pipeline` is the
# single entry point both a future API route and a future Celery task will
# call, unchanged.

from app.pipeline.runner import run_pipeline  # noqa: F401
