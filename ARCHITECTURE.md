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
                        │ SQLAlchemy models /  │
                        │ repositories         │
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
        pipeline.py  # POST /api/pipeline/run, GET /api/pipeline/runs
        drones.py    # GET /api/drones, GET /api/drones/{id}
        stats.py     # GET /api/stats (optional/bonus)
      deps.py         # FastAPI dependency-injection helpers (e.g. DB session)
      main.py         # FastAPI app instance, router registration, CORS, etc.

    pipeline/        # Framework-independent pipeline logic.
                     # No import of FastAPI or Celery anywhere in this package.
      runner.py       # Orchestrates load -> validate -> normalize -> persist
                       # -> update run status. This is the function/class that
                       # both FastAPI and (later) Celery will call.
      loader.py        # Reads raw records from the JSON input source.
      validator.py      # Applies validation rules; separates valid/invalid.
      normalizer.py      # Normalizes accepted records (e.g. timestamp parsing,
                          # trimming, casing) before persistence.

    models/          # SQLAlchemy ORM models (DroneTelemetry, PipelineRun).
    schemas/         # Pydantic schemas for API request/response shapes.
                     # Kept separate from ORM models (API shape != DB shape).
    repositories/    # Persistence-facing helper functions/classes that wrap
                     # SQLAlchemy queries (e.g. insert telemetry, list with
                     # filters, record a pipeline run). Business/pipeline code
                     # talks to repositories, not directly to raw SQLAlchemy
                     # sessions/queries, keeping persistence swappable.
    db/
      session.py      # SQLAlchemy engine/session setup.
      base.py          # Declarative base shared by models.

  alembic/           # Migration scripts (schema managed via Alembic, not
                     # create_all()).
  tests/             # Pytest tests, mirroring the app/ structure.
  data/              # Sample JSON input file(s) for the pipeline.
```

### Why separate `pipeline/` from `api/`

- `api/` translates HTTP requests into calls against the pipeline/repository
  layer, and translates results back into HTTP responses. It should contain
  no validation/normalization/persistence logic of its own.
- `pipeline/` contains the actual ingestion logic and has zero knowledge of
  HTTP, FastAPI, or Celery. It receives plain Python inputs (e.g. a file
  path) and a DB session/repository, and returns a plain result (counts,
  status). This is what lets a future Celery task call
  `pipeline.runner.run_pipeline(...)` with no changes to that function.
- `models/` (SQLAlchemy) vs `schemas/` (Pydantic) are kept distinct because
  the database shape and the public API shape are allowed to evolve
  independently (e.g. internal columns that are never exposed via the API).

### Pipeline Stages (conceptual)

1. **Load** — read raw records from the JSON file (or, later, other sources)
   into plain Python dicts/objects. No validation yet.
2. **Validate** — apply the validation rules from
   [`PROJECT_CONTEXT.md`](./PROJECT_CONTEXT.md); split records into
   valid/invalid, counting each.
3. **Normalize** — for valid records only, normalize field representations
   (e.g. parse `timestamp` into a real datetime, trim strings) before they
   reach persistence.
4. **Persist** — store all valid, normalized records via the repository
   layer. Every telemetry record is stored (not just the latest per drone),
   so path history and "latest position" views can both be derived later
   from the same table.
5. **Update pipeline run status** — write a `PipelineRun` row capturing
   `started_at`, `finished_at`, `status`, `total_records`, `valid_records`,
   `invalid_records`, and `error_message` if the run failed outright.

### Data Model (conceptual, subject to refinement during implementation)

- **`DroneTelemetry`** (one row per ingested telemetry record — full
  history, not just latest-per-drone): `id`, `drone_id`, `drone_type`,
  `operator_id`, `latitude`, `longitude`, `altitude_m`, `speed_kmh`,
  `battery_percent`, `timestamp`, `status`, plus bookkeeping like
  `created_at`.
- **`PipelineRun`**: `id`, `started_at`, `finished_at`, `status`,
  `total_records`, `valid_records`, `invalid_records`, `error_message`.

Storing full history (rather than upserting latest-per-drone) is a deliberate
choice so that "drone path history" and "latest position" bonus features are
just different queries over the same table, instead of requiring a schema
change later.

### Database Access

- SQLAlchemy models + a thin repository layer are the only code that issues
  queries. Business/pipeline code calls repository functions, never raw
  `session.query(...)` calls directly, so PostgreSQL specifics stay isolated
  behind SQLAlchemy.
- Schema is managed via Alembic migrations from the start (not
  `Base.metadata.create_all()`), since migrations are an explicit deliverable
  and this also prepares cleanly for Docker Compose + CI use later.

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

- Exact Pydantic schema field names/types (decided during backend
  implementation phase).
- Exact Alembic migration structure (created when backend implementation
  starts).
- Exact Angular component boundaries beyond the sketch above (refined during
  frontend implementation phase).
- Docker Compose file contents (bonus phase).
- Celery/Redis wiring details (bonus phase).

These are intentionally deferred per the agreed workflow: implement only the
phase that's explicitly requested.
