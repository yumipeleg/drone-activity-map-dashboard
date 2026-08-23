"""Shared pytest setup: points the whole test process at a dedicated
PostgreSQL database instead of the real development database.

How the test database is selected
----------------------------------
`app/config.py` builds a single `Settings` object at import time from the
`DATABASE_URL` environment variable (falling back to `backend/.env`), and
`app/db/session.py` builds its SQLAlchemy `engine`/`SessionLocal` from that
`Settings` object, also at import time. Both only happen once per process.

So, before anything under `app.*` gets imported anywhere in the test
session, this file reads `DATABASE_URL` out of `backend/.env` *without*
triggering that import (via `dotenv.dotenv_values`, which just parses the
file), swaps the database name for "drone_activity_test", and sets that as
the real `DATABASE_URL` environment variable. Because real environment
variables take priority over `.env` file values in pydantic-settings, every
later import of `app.config` / `app.db.session` — including the one inside
`run_pipeline()`, which opens its own session directly and is not reachable
through FastAPI dependency overrides — ends up talking to
"drone_activity_test" on the same PostgreSQL server, never to the real
"drone_activity" database.

How its schema is prepared
---------------------------
The `_prepare_test_database` fixture below (session-scoped, autouse) makes
sure the "drone_activity_test" database itself exists (creating it via a
throwaway connection to the always-present "postgres" maintenance database
if needed), then calls `Base.metadata.create_all()` to create the
`drone_telemetry` / `pipeline_run` tables directly from the current
SQLAlchemy models — not via Alembic. That is a deliberate simplification
for tests only: the schema stays correct as long as the models do, with no
migration history to maintain for a throwaway database. The real
development database still goes through Alembic as normal. `create_all()`
is safe to call every session — it skips tables that already exist — so if
the models ever change shape, drop `drone_activity_test` once and it will
be recreated automatically on the next test run.

How tests clean/isolate their records
--------------------------------------
The `clean_pipeline_tables` fixture below (autouse, applied to every test)
wipes `drone_telemetry` and `pipeline_run` before and after each test. This
is only safe to do unconditionally because those tables now live in
"drone_activity_test", never in the real development database.

How to run tests safely
------------------------
Just run pytest normally (see the project README/AGENTS.md for the exact
command) with the PostgreSQL container from `docker-compose.yml` running.
No extra setup step is required — this file creates the test database and
its schema automatically the first time the suite runs.
"""

import os
from pathlib import Path

from dotenv import dotenv_values

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_TEST_DB_NAME = "drone_activity_test"


def _test_database_url() -> str:
    dev_env = dotenv_values(_BACKEND_DIR / ".env")
    dev_url = dev_env.get("DATABASE_URL")
    if not dev_url:
        raise RuntimeError(
            "DATABASE_URL not found in backend/.env — cannot derive a test database URL"
        )
    base_url, _, _dev_db_name = dev_url.rpartition("/")
    return f"{base_url}/{_TEST_DB_NAME}"


# Must happen before any `app.*` module is imported anywhere in the test
# session — see the module docstring above.
os.environ["DATABASE_URL"] = _test_database_url()

import pytest  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

import app.models  # noqa: E402,F401 - registers all tables on Base.metadata
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.models.drone_telemetry import DroneTelemetry  # noqa: E402
from app.models.pipeline_run import PipelineRun  # noqa: E402


def _ensure_test_database_exists() -> None:
    """Create the "drone_activity_test" database if it isn't there yet.

    Connects to the "postgres" maintenance database instead, since a
    connection can't issue `CREATE DATABASE` for the database it's
    currently connected to.
    """
    admin_url = os.environ["DATABASE_URL"].rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": _TEST_DB_NAME},
            ).first()
            if exists is None:
                connection.execute(text(f'CREATE DATABASE "{_TEST_DB_NAME}"'))
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _prepare_test_database():
    """Runs once per test session: ensure the test database and its
    schema (tables/constraints/indexes) exist before any test runs.
    """
    _ensure_test_database_exists()
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(autouse=True)
def clean_pipeline_tables():
    """Wipe drone_telemetry/pipeline_run before and after every test.

    Safe unconditionally: this always runs against "drone_activity_test"
    (see the DATABASE_URL override at the top of this file), never the
    real development database.
    """
    _wipe_pipeline_tables()
    yield
    _wipe_pipeline_tables()


def _wipe_pipeline_tables() -> None:
    with SessionLocal() as db:
        db.query(DroneTelemetry).delete()
        db.query(PipelineRun).delete()
        db.commit()
