# Project Context — Drone Activity Map Dashboard

## Origin

This project is a take-home Full Stack technical exercise. The full, original
requirements are in [`EXERCISE.md`](./EXERCISE.md). This document summarizes
those requirements plus the technical decisions we've agreed on, so future
work (by a human or an AI agent) has a single source of truth without
re-reading the raw exercise brief each time.

## Objective

Build a small full-stack application that:

1. Ingests simulated drone telemetry records from a JSON or CSV file.
2. Validates, normalizes, and persists them via a Python backend pipeline.
3. Exposes the processed data through a REST API.
4. Displays drone positions on a map in an Angular frontend, with filtering
   and a pipeline control panel.

Coordinates may be real map coordinates; the drone activity itself is
simulated and does not represent real operations.

## Example Drone Record

```json
{
  "drone_id": "DRONE-001",
  "drone_type": "Quadcopter",
  "operator_id": "OP-123",
  "latitude": 32.0853,
  "longitude": 34.7818,
  "altitude_m": 120,
  "speed_kmh": 45,
  "battery_percent": 76,
  "timestamp": "2026-06-28T10:30:00Z",
  "status": "active"
}
```

## Validation Rules

- `drone_id` must not be empty.
- `latitude` must be between -90 and 90.
- `longitude` must be between -180 and 180.
- `altitude_m` must be zero or positive.
- `battery_percent` must be between 0 and 100.
- `timestamp` must be a valid date/time value.
- `status` must be one of: `active`, `landed`, `lost_signal`.

Invalid individual records are skipped and counted; they do not fail the
whole pipeline run.

## Pipeline Run Status

A history of pipeline executions is stored, with at least:

| Field           | Description                                  |
|-----------------|-----------------------------------------------|
| id              | Unique pipeline run identifier                |
| started_at      | Pipeline start time                           |
| finished_at     | Pipeline finish time                          |
| status          | `queued`, `started`, `completed`, or `failed` |
| total_records   | Number of records read from input             |
| valid_records   | Number of records inserted successfully        |
| invalid_records | Number of records skipped due to validation    |
| error_message   | Failure details, if any                       |

## API Endpoints (suggested by the exercise)

| Method | Endpoint             | Purpose                                   |
|--------|-----------------------|--------------------------------------------|
| POST   | `/api/pipeline/run`  | Trigger the data ingestion pipeline.      |
| GET    | `/api/pipeline/runs` | Return recent pipeline execution history. |
| GET    | `/api/drones`        | Return drone records, with optional filters. |
| GET    | `/api/drones/{id}`   | Return a single drone record.             |
| GET    | `/api/stats`         | Optional: return summary statistics.      |

`/api/drones` filters: `drone_type`, `status`, `operator_id`, `min_battery`,
`from`/`to` date range.

## Frontend Requirements

- **Map dashboard**: markers per drone position; clicking a marker opens a
  popup with drone ID, type, operator ID, altitude, speed, battery
  percentage, status, and last update timestamp.
- **Filters**: drone type, status, operator ID, minimum battery percentage,
  date range — calling the backend API and refreshing map results.
- **Pipeline control panel**: a "Run Pipeline" action that calls
  `POST /api/pipeline/run`, then refreshes the drone list and a pipeline-run
  history table (date, status, valid records, invalid records).

## Deliverables (per the exercise)

- Backend source code.
- Frontend source code.
- README with setup and run instructions.
- Database schema or migrations.
- Example input file with valid and invalid records.
- Short explanation of the pipeline flow.
- Basic tests for important backend and frontend logic.

## Agreed Technical Decisions

### Frontend

- Angular 21, standalone architecture (no `NgModule`s).
- Leaflet for the map.
- Angular services + signals; reactive forms where appropriate.
- No NgRx.
- No Angular Material or other UI framework, unless explicitly requested
  later.

### Backend

- Python, FastAPI.
- SQLAlchemy as the persistence layer.
- PostgreSQL as the database.
- Alembic for migrations.
- Pydantic for API/data validation.

### Pipeline

- JSON or CSV files from a runtime input directory (`input/` at repo root,
  bind-mounted into backend/worker containers). Files can be added or replaced
  without rebuilding or restarting the stack.
- Pipeline logic is independent from the API layer (see
  [`ARCHITECTURE.md`](./ARCHITECTURE.md)).
- Conceptual stages: `load -> validate -> normalize -> persist -> update
  pipeline run status`.
- Invalid individual records are skipped and counted, not fatal to the run.
- All telemetry records are stored (full history), not only the latest
  position per drone — this keeps the door open for path-history and
  latest-position bonus features without a data model change.

### Database

- PostgreSQL, chosen because the final target includes Docker Compose and a
  separate background worker (Celery), and we want one database story across
  local dev and that target architecture.
- Persistence is kept behind SQLAlchemy so application/business logic is not
  tightly coupled to PostgreSQL specifics.

### Bonus Features

Implemented (Day 4) — see [`ARCHITECTURE.md`](./ARCHITECTURE.md) for details:

- Latest drone position per drone (`GET /api/drones?latest_only=true`,
  always used by the map — no user-facing toggle).
- Drone path history (`GET /api/drones/{drone_id}/history`, drawn as a
  non-interactive polyline plus historical point markers when a marker is
  selected; single-point histories show only the fleet marker and a
  dedicated status message).
- Pagination on `GET /api/drones` (`page`/`page_size`, bypassed for
  `latest_only=true`).
- Low-battery highlighting (`battery_percent < 20`, strictly) and
  lost-signal highlighting, via `L.circleMarker` styling.
- `GET /api/stats` backend endpoint and fleet-wide summary semantics.
- Meaningful unit/integration tests for all of the above.

Implemented (Day 5):

- Celery background worker + Redis broker for async pipeline execution
  (`POST /api/pipeline/run` → HTTP 202 → worker → frontend polling).
- Runtime pipeline input file selection (`GET /api/pipeline/inputs`, optional
  `input_file` on `POST /api/pipeline/run`, `PipelineRun.input_file` stored as
  the logical filename).
- Full Docker Compose stack (`db`, `redis`, `backend`, `worker`, `frontend`).
  Backend runs Alembic migrations on startup before serving.
- Root [`README.md`](./README.md) with Docker Compose quick start and test instructions.

### Important Architectural Rule

The core pipeline runner must **not** depend on FastAPI or Celery, so that the
Celery task invokes the exact same pipeline logic without rewriting it.
FastAPI enqueues the run; the worker calls `execute_pipeline_run`. Neither
owns the pipeline logic itself.

## Code Quality Principles

- Keep the architecture simple and readable; do not over-engineer.
- Separate API, business logic, pipeline logic, and persistence
  responsibilities.
- Do not add technologies or patterns that are not needed.
- Do not implement bonus features until explicitly requested, but avoid
  choices that would block them later.
- Favor clarity for an experienced Java/TypeScript developer who is newer to
  Python.

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for how these decisions map to
concrete module/folder structure, and [`AGENTS.md`](./AGENTS.md) for how an
AI coding agent should work on this repository.
