"""Celery tasks — thin wrappers around the framework-independent pipeline runner.

Pipeline processing logic lives in `app.pipeline.runner`; this module only
bridges Celery to `execute_pipeline_run(run_id)`.
"""

from app.celery_app import celery_app
from app.pipeline.runner import execute_pipeline_run


@celery_app.task(name="pipeline.execute_run")
def run_pipeline_task(run_id: int) -> None:
    execute_pipeline_run(run_id)
