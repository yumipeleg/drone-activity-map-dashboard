# Drone Activity Map Dashboard

Angular + FastAPI application for ingesting simulated drone telemetry from JSON,
persisting full event history in PostgreSQL, and displaying the latest fleet state
on a Leaflet map with filtering and path history. Pipeline ingestion runs
asynchronously via Celery and Redis; the UI polls run status until completion.

## Quick Start

From the repository root:

```bash
docker compose up --build
```

When services are up:

- **Frontend:** http://localhost:4200
- **API:** http://localhost:8000

Stop the stack:

```bash
docker compose down
```

Full data reset (deletes the PostgreSQL volume):

```bash
docker compose down -v
```

`docker compose down -v` deletes all PostgreSQL data stored in the Docker volume.

**Troubleshooting:** Stop any local processes already using ports **4200**, **8000**, or **5432** before starting Compose (for example a local `ng serve`, `uvicorn`, or PostgreSQL instance).

Compose starts PostgreSQL, Redis, the FastAPI backend (Alembic migrations run on startup), a Celery worker, and the Angular frontend — no separate Python or npm setup is required for evaluation.

## Local Development (Optional)

Docker Compose above remains the recommended evaluator path. Running components individually requires installing dependencies and copying `backend/.env.example` to `backend/.env`.

Start only the infrastructure services:

```bash
docker compose up db redis -d
cd backend
pip install -r requirements-dev.txt
alembic upgrade head
```

Backend API (from `backend/`):

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Celery worker — required for `POST /api/pipeline/run` to complete (from `backend/`):

```bash
celery -A app.celery_app worker --loglevel=info
```

On native Windows, add `--pool=solo` (Celery's default prefork pool is not supported there).

Frontend dev server (from `frontend/`):

```bash
npm install
npm start
```

API: http://localhost:8000 · Frontend: http://localhost:4200

## What to Try

- Click **Run Pipeline** and watch status move from `queued` → `started` → `completed` or `failed`.
- Apply drone filters (type, status, operator, battery, date range) and refresh the map.
- Click a drone marker to view its path history.
- Inspect **Pipeline Run History** for past executions.

## Architecture

```
Browser / Angular
       |
       v
    FastAPI
    /     \
Postgres  Redis
            |
            v
       Celery Worker
            |
            v
      PipelineRunner
            |
            v
         Postgres
```

PostgreSQL stores all telemetry events and `PipelineRun` business state. Redis is the Celery broker only — not a source of truth for run status. Celery executes ingestion in the background. Angular polls `GET /api/pipeline/runs/{id}` every second until the run reaches a terminal status, then refreshes the map and run history.

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for deeper design notes.

## Pipeline Flow

```
JSON → validation → normalization → duplicate detection → persist valid telemetry → update PipelineRun
```

Invalid records are skipped and counted; duplicates are counted separately. Execution is asynchronous: `POST /api/pipeline/run` returns immediately with HTTP 202 while a worker processes the file. Valid rows are committed individually, so a later processing failure can leave already-persisted telemetry in the database.

## Key Features

- Leaflet drone map with latest position per drone
- Backend filters and pagination on `GET /api/drones`
- Low-battery and lost-signal marker styling
- Drone path history polyline and historical points
- Fleet stats endpoint (`GET /api/stats`)
- Celery/Redis background pipeline
- Docker Compose full stack
- Automated backend and frontend tests

## Key Design Decisions / Trade-offs

- All telemetry events are stored; latest map state is derived by query (`latest_only=true`).
- Latest-row selection happens before filters are applied — filters match each drone's current state, not historical rows.
- `latest_only=true` returns the full current fleet (pagination is bypassed for the map view).
- PostgreSQL is the source of truth for `PipelineRun` status; Redis is the Celery broker only.
- The UI blocks starting a second pipeline while one is in progress.
- `started_at` is set when the run is accepted (including queue wait); the worker sets `finished_at` on completion or failure.
- Per-record commits mean a failed run may leave already-persisted telemetry visible on the map.

## API Highlights

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/pipeline/run` | Enqueue ingestion — returns **HTTP 202** with a `queued` run |
| GET | `/api/pipeline/runs` | Recent pipeline run history |
| GET | `/api/pipeline/runs/{id}` | Single run (used by frontend polling) |
| GET | `/api/drones` | Filtered drone telemetry (supports `latest_only`, pagination) |
| GET | `/api/drones/{drone_id}/history` | Path history for one drone |
| GET | `/api/drones/{telemetry_id}` | Get a telemetry record by its database ID. |
| GET | `/api/stats` | Fleet-wide summary statistics |
| GET | `/health` | Health check |

## Tests

### Backend

Requires a running PostgreSQL instance (the Compose `db` service is sufficient), `backend/.env` copied from `.env.example`, and dependencies installed in a virtualenv (`pip install -r requirements-dev.txt`). Tests automatically use a separate `drone_activity_test` database.

```bash
cd backend
python -m pytest
```

**63 tests passing.**

### Frontend

```bash
cd frontend
npm test -- --watch=false
npm run build
```

**69 tests passing.**

## Assumptions

- Default pipeline input is `backend/data/sample_drones.json` (bundled in the backend Docker image at `/app/data/sample_drones.json`).
- Timestamps without a timezone offset are treated as UTC during validation.
- Docker Compose is the recommended path for reviewers; local Python/npm development is supported but not required for evaluation.
