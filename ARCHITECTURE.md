# Architecture

This document describes the intended structure of the application. It is
written before any application code exists, so treat it as the target shape
to implement incrementally, phase by phase — not as a description of code
that already exists.

For the "what" and "why" of the product requirements, see
[`PROJECT_CONTEXT.md`](./PROJECT_CONTEXT.md). This document focuses on the
"how" of the code structure.

## High-Level Overview

```
                        ┌────────────────────┐
                        │   Angular frontend  │
                        │  (Leaflet map, UI)  │
                        └──────────┬──────────┘
                                   │ HTTP (JSON)
                                   ▼
                        ┌────────────────────┐
                        │   FastAPI app       │
                        │  (API layer only)   │
                        └──────────┬──────────┘
                                   │ calls
                                   ▼
                        ┌────────────────────┐
                        │  Pipeline runner    │
                        │ (framework-free)    │
                        └──────────┬──────────┘
                                   │ uses
                                   ▼
                        ┌────────────────────┐
                        │ services / SQLAlchemy │
                        │ models               │
                        └──────────┬──────────┘
                                   │
                                   ▼
                        ┌────────────────────┐
                        │    PostgreSQL        │
                        └────────────────────┘
```

The key rule driving this shape: **the pipeline runner must not depend on
FastAPI or Celery**. FastAPI (today) and Celery (later, as a bonus) are both
just *callers* of the same pipeline function/class. This is why the pipeline
lives in its own module, independent of the `api/` package.

## Backend Structure (`backend/`)

Planned layout (created incrementally, not all at once):

```
backend/
  app/
    api/            # FastAPI routers — HTTP concerns only (request/response,
                     # status codes, wiring). No business logic here.
      routes/
        pipeline.py  # POST /api/pipeline/run, GET /api/pipeline/runs,
                     # GET /api/pipeline/runs/{run_id} (implemented, Phase 2B)
        drones.py    # GET /api/drones, GET /api/drones/{telemetry_id}
                     # (implemented, Phase 2B)
        stats.py     # GET /api/stats (optional/bonus, not implemented)
      main.py         # FastAPI app instance, router registration, CORS, etc.

    services/        # Thin query/business-operation functions between
                     # routes and the database (route -> service ->
                     # SQLAlchemy). Implemented, Phase 2B.
      pipeline_runs.py # list_pipeline_runs(), get_pipeline_run()
      drones.py        # list_drone_telemetry() (builds one filtered SQL
                       # query from optional criteria), get_drone_telemetry()

    pipeline/        # Framework-independent pipeline logic (implemented).
                     # No import of FastAPI or Celery anywhere in this package.
      runner.py       # run_pipeline(): orchestrates load -> normalize/validate
                       # -> detect duplicates -> persist -> update run status.
                       # This is the function both FastAPI and (later) Celery
                       # will call, unchanged.
      loader.py        # Reads raw records from the JSON input source; raises
                        # InputLoadError only for a file-level problem (a bad
                        # individual record is never this module's concern).

    models/          # SQLAlchemy ORM models (DroneTelemetry, PipelineRun).
    schemas/         # Pydantic schemas for API/pipeline input AND output.
                     # Kept separate from ORM models (API shape != DB shape).
                     # DroneTelemetryInput also owns normalization (whitespace
                     # trimming, status casing, UTC-defaulting naive
                     # timestamps) via Pydantic's own model config / validators
                     # — there is no separate normalizer.py module, since
                     # Pydantic v2 already covers the "clearly safe"
                     # normalization needed here without an extra layer.
                     # DroneTelemetryRead / PipelineRunRead (implemented,
                     # Phase 2B) are the API *response* shapes — separate
                     # from DroneTelemetryInput, which validates raw
                     # pipeline input and is never returned by the API.
                     # DroneTelemetryFilters groups the optional
                     # GET /api/drones query parameters.
    db/
      session.py      # SQLAlchemy engine/session setup.
      base.py          # Declarative base shared by models.

  alembic/           # Migration scripts (schema managed via Alembic, not
                     # create_all() — except for the dedicated test
                     # database, see "Testing" below).
  tests/             # Pytest tests, mirroring the app/ structure. Includes
                     # conftest.py, which selects/prepares the dedicated
                     # test database for the whole suite (Phase 2B).
  data/              # Sample JSON input file for the pipeline
                     # (sample_drones.json).
```

Note: a `repositories/` layer was sketched here originally but has not been added. `app/services/` (added in Phase 2B) covers the actual need instead — thin functions that build one SQLAlchemy query per read operation for the API routes. The pipeline runner still talks directly to `SessionLocal`, `DroneTelemetry`, and `PipelineRun` via plain SQLAlchemy, since it is a self-contained writer with its own transaction/duplicate-handling concerns that don't overlap with the read-only service functions. A repository layer would only be worth introducing if write-side query logic ever needed to be shared across more than one call-site, which is not the case here.

### Why separate `pipeline/` from `api/`

- `api/` translates HTTP requests into calls against the pipeline/service
  layer, and translates results back into HTTP responses. It should contain
  no validation/normalization/persistence logic of its own.
- `pipeline/` contains the actual ingestion logic and has zero knowledge of
  HTTP, FastAPI, or Celery. It receives a plain file path, owns its own DB
  session internally, and returns a plain result object (counts, status).
  This is what lets a future Celery task call
  `pipeline.runner.run_pipeline(...)` with no changes to that function.
- `models/` (SQLAlchemy) vs `schemas/` (Pydantic) are kept distinct because
  the database shape and the public API shape are allowed to evolve
  independently (e.g. internal columns that are never exposed via the API).

### Pipeline Stages (finalized in Phase 2A — `backend/app/pipeline/runner.py`)

1. **Load** — `loader.load_raw_records()` reads the JSON file into plain
   Python dicts. A file-level problem (missing file, invalid JSON, wrong
   top-level shape) raises `InputLoadError`, which fails the whole run; an
   individual record's content is never inspected at this stage.
2. **Normalize + validate** — each raw record is passed to
   `DroneTelemetryInput.model_validate()` (see `app/schemas/drone_telemetry.py`).
   Conservative normalization (whitespace trimming, status-casing, UTC
   defaulting for naive timestamps) happens inside the same Pydantic call,
   before the corresponding field's range/allowed-value check. A record that
   fails is counted in `invalid_records` and skipped — it never fails the run.
3. **Detect duplicates** — one batched query fetches exactly the
   `(drone_id, timestamp)` pairs already in the database that match pairs
   present in this run's validated batch (not each drone's full history);
   combined with an in-memory set updated as records are inserted, this
   catches duplicates against prior runs *and* duplicates repeated within
   the same input file. A duplicate is counted in `duplicate_records` and
   skipped — the DB's own unique constraint remains a final safety net if a
   race ever slips past this check.
4. **Persist** — each valid, non-duplicate record is inserted and committed
   individually (not batched into one large transaction), so that if a
   later record hits an unexpected fatal error, telemetry already committed
   earlier in the same run is not lost. Every telemetry record is stored
   (not just the latest per drone), so path history and "latest position"
   views can both be derived later from the same table.
5. **Update pipeline run status** — a `PipelineRun` row is created at the
   start (`status=started`) and updated once at the end, to either
   `completed` (with final counters) or `failed` (with an `error_message`,
   after rolling back any broken transaction state first).

### Data Model (finalized in Phase 1C — `backend/app/models/`)

- **`DroneTelemetry`** (one row per ingested telemetry record — full
  history, not just latest-per-drone): `id`, `drone_id`, `drone_type`,
  `operator_id`, `latitude`, `longitude`, `altitude_m`, `speed_kmh`,
  `battery_percent`, `timestamp` (event time, timezone-aware), `status`,
  and `created_at` (row-insertion bookkeeping, distinct from `timestamp`).
  A composite **unique constraint on `(drone_id, timestamp)`** is the
  duplicate-event identity rule: re-running the same input file is safe
  because an already-stored `(drone_id, timestamp)` pair is skipped rather
  than inserted twice. That same pair also serves as the index used for
  path-history queries (`drone_id` equality + `timestamp` ordering).
  Additional single-column indexes exist on `status`, `operator_id`,
  `drone_type`, and `timestamp` to support the required API filters.
- **`PipelineRun`**: `id`, `started_at`, `finished_at` (nullable while
  running), `status`, `total_records`, `valid_records`, `invalid_records`,
  `duplicate_records` (otherwise-valid records skipped as already-existing
  events), `error_message`. The four counters default to `0` at the
  database level. No foreign key or relationship exists between
  `PipelineRun` and `DroneTelemetry` — the exercise requires pipeline
  execution history, not per-record ingestion lineage, so the two tables
  are deliberately kept independent. That can be revisited additively
  later if a concrete lineage requirement ever appears.
- **Status enums** (`DroneStatus`, `PipelineRunStatus`, in
  `app/models/enums.py`): plain Python string enums stored as `VARCHAR`
  columns with an explicit `CHECK` constraint (SQLAlchemy
  `Enum(..., native_enum=False, create_constraint=True)`), rather than a
  native PostgreSQL enum type — simpler to read, migrate, and evolve for
  this project's scale. Each column stores the actual exercise string
  values (`"active"`, `"lost_signal"`, etc.), not the Python member names.

Storing full history (rather than upserting latest-per-drone) is a deliberate
choice so that "drone path history" and "latest position" bonus features are
just different queries over the same table, instead of requiring a schema
change later.

### Database Access

- All queries go through SQLAlchemy (never raw SQL strings), so PostgreSQL
  specifics stay isolated behind the ORM. The pipeline runner is the only
  writer and queries `DroneTelemetry`/`PipelineRun` directly via
  `SessionLocal` (see the note under "Backend Structure" above for why it
  doesn't go through `app/services/`). API read queries go through
  `app/services/` instead (see "REST API Layer" below). No repository
  layer exists — introduce one only if write-side query logic ever needs
  to be shared across more than one call-site.
- Schema is managed via Alembic migrations from the start (not
  `Base.metadata.create_all()`), since migrations are an explicit deliverable
  and this also prepares cleanly for Docker Compose + CI use later.

### REST API Layer (finalized in Phase 2B — `backend/app/api/`, `services/`, `schemas/`)

Every route follows **route → service → SQLAlchemy** and returns an explicit
Pydantic response schema (never a raw ORM object):

- `POST /api/pipeline/run` — calls `pipeline.runner.run_pipeline()` directly
  (no service layer involved; the runner already owns its own session/
  transactions). `run_pipeline()` returns a `PipelineResult`, which lacks
  `started_at`/`finished_at` (its own DB session is already closed by the
  time it returns). Rather than adding a second, slightly different
  response schema just for this one endpoint, the route re-fetches the same
  row by `PipelineResult.pipeline_run_id` via
  `services.pipeline_runs.get_pipeline_run()` and returns it as a
  `PipelineRunRead` — the same schema the two `GET` endpoints below use, so
  "a pipeline run" is one consistent shape everywhere. Always returns
  **HTTP 200**, even when the run's own persisted `status` is `failed` —
  that's a normal, fully persisted domain outcome, not an HTTP error. An
  infrastructure failure severe enough that `run_pipeline()` couldn't even
  create its `PipelineRun` row surfaces as an actual **HTTP 500** via
  FastAPI's default unhandled-exception behavior. Kept easy to evolve to
  `HTTP 202` + `run_id` once Celery is added.
- `GET /api/pipeline/runs` — `services.pipeline_runs.list_pipeline_runs()`,
  most-recent-first, capped by an optional `limit` query parameter
  (default 20). No pagination beyond that cap yet.
- `GET /api/pipeline/runs/{run_id}` — `services.pipeline_runs.get_pipeline_run()`,
  **HTTP 404** if missing. Added ahead of the exercise's explicit
  requirements as future preparation for Celery polling.
- `GET /api/drones` — `services.drones.list_drone_telemetry()` builds one
  SQLAlchemy query with a `.where()` added per provided (optional) filter —
  `drone_type`, `status`, `operator_id`, `min_battery`, and a `from`/`to`
  date range — never filtering in Python after loading rows. Filters are
  grouped into a `DroneTelemetryFilters` schema instance built by the route
  from individual FastAPI query parameters (kept as individual parameters,
  not a `Depends()`-injected query model, for straightforward
  alias handling of the `from`/`to` reserved-word parameter names). The
  public `?from=YYYY-MM-DD&to=YYYY-MM-DD` parameters are plain calendar
  dates; internally they become timezone-aware UTC boundaries:
  `timestamp >= start_of(from)` and `timestamp < start_of(to + 1 day)` — an
  exclusive upper bound, not a fragile `<= 23:59:59.999999` comparison.
  Returns individual telemetry rows (most recent first), not "latest
  position per drone" — that is a separate, not-yet-implemented feature.
- `GET /api/drones/{telemetry_id}` — `services.drones.get_drone_telemetry()`,
  **HTTP 404** if missing. `{telemetry_id}` is the `DroneTelemetry` row's own
  internal integer primary key (`id`), *not* the business `drone_id` — one
  `drone_id` can have many rows over time. A future business-drone history
  endpoint is expected to live at a separate route such as
  `/api/drones/{drone_id}/history` rather than overloading this one.

Invalid query parameter values (e.g. `min_battery=500`, an unknown
`status`, a non-integer path id) are rejected with FastAPI/Pydantic's
default **HTTP 422** — no custom validation/error framework was added.

### Testing (finalized in Phase 2B — `backend/tests/conftest.py`)

The whole test process is pointed at a dedicated `drone_activity_test`
database on the *same* PostgreSQL server as development, so the test suite
never touches the real `drone_activity` data:

- `conftest.py` reads `DATABASE_URL` out of `backend/.env` (without
  importing `app.config`) and overrides the real `DATABASE_URL` environment
  variable to point at `drone_activity_test`, before any `app.*` module is
  imported anywhere in the test session. Because `app/config.py` and
  `app/db/session.py` each build their singleton (`Settings`, `engine`/
  `SessionLocal`) once at import time, and because real environment
  variables take priority over `.env` file values, this one override
  redirects *all* database access for the whole process — including
  `run_pipeline()`'s own internal session, which isn't reachable through
  FastAPI dependency overrides since it isn't a `Depends()`-injected
  session.
- A session-scoped autouse fixture creates the `drone_activity_test`
  database itself if missing (via a throwaway connection to the always-
  present `postgres` maintenance database), then calls
  `Base.metadata.create_all()` to create its tables/constraints/indexes
  directly from the current SQLAlchemy models — not via Alembic. This is a
  deliberate simplification scoped to the test database only; the real
  development database still goes through Alembic normally.
- A function-scoped autouse fixture wipes `drone_telemetry`/`pipeline_run`
  before and after every test, safe to do unconditionally since those
  tables now always belong to `drone_activity_test`.
- Running the suite requires no extra setup beyond the PostgreSQL container
  from `docker-compose.yml` being up — the test database and schema are
  created automatically on first run. If a model's shape changes, drop
  `drone_activity_test` once and it is recreated automatically next run.

## Frontend Structure (`frontend/`)

Planned layout (Angular 21, standalone components, no NgModules):

```
frontend/
  src/
    app/
      core/            # Singleton services usable app-wide.
        drones.service.ts        # HTTP calls to /api/drones*
        pipeline.service.ts      # HTTP calls to /api/pipeline/*
        models/                  # TypeScript interfaces mirroring API schemas
      features/
        map-dashboard/           # Main dashboard page/feature.
          map/                    # Leaflet map component (markers, popups)
          filters/                # Filter form component (reactive forms)
          pipeline-panel/         # "Run Pipeline" + run-history table
      app.component.ts
      app.routes.ts
      app.config.ts              # Standalone bootstrap config, providers
```

### State Approach

- No NgRx. Component/page-level state is held in Angular **signals**,
  populated by calling services in `core/`.
- Services encapsulate HTTP calls and expose signals (or plain observables
  converted to signals) for the current drone list, filter state, and
  pipeline run history. Components read/write signals; they don't talk to
  `HttpClient` directly.
- Filters are modeled as a Reactive Form; form value changes drive a call to
  `DronesService` to refetch filtered results.

## Pipeline / Worker Evolution Path (for later bonus phases)

1. **Now**: FastAPI's `POST /api/pipeline/run` calls
   `pipeline.runner.run_pipeline(...)` synchronously in-process.
2. **Later (bonus)**: a Celery task wraps the same
   `pipeline.runner.run_pipeline(...)` call; FastAPI enqueues the task
   instead of running it inline. Redis is the broker. No pipeline code
   changes — only a new thin Celery task module and a change in what the API
   route calls.

This evolution is only possible because the pipeline runner was never given
a FastAPI or Celery dependency in the first place.

## What Is Deliberately Not Decided Yet

- `/api/stats` endpoint (bonus, not yet designed).
- Pagination beyond `GET /api/pipeline/runs`'s simple `limit` cap.
- "Latest position per drone" and drone path-history (`/api/drones/{drone_id}/history`)
  endpoints — the current schema/queries support them without a redesign,
  but neither is implemented yet.
- Exact Angular component boundaries beyond the sketch above (refined during
  frontend implementation phase).
- Docker Compose file contents beyond PostgreSQL (bonus phase — `backend`,
  `worker`, `redis`, `frontend` services).
- Celery/Redis wiring details (bonus phase).

These are intentionally deferred per the agreed workflow: implement only the
phase that's explicitly requested.
