"""Celery application — Redis broker only, no result backend.

Both the FastAPI process and a Celery worker import the same
`app.config.settings`, so `CELERY_BROKER_URL` / `celery_broker_url` is
shared via the usual `.env` mechanism.
"""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "drone_activity",
    broker=settings.celery_broker_url,
    include=["app.tasks"],
)
