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
        drones.py    # GET /api/drones (latest_only + pagination),
                     # GET /api/drones/{drone_id}/history,
                     # GET /api/drones/{telemetry_id} (implemented, Day 4)
        stats.py     # GET /api/stats (implemented, Day 4)
      main.py         # FastAPI app instance, router registration, CORS, etc.

    services/        # Thin query/business-operation functions between
                     # routes and the database (route -> service ->
                     # SQLAlchemy). Implemented, Phase 2B; extended Day 4.
      pipeline_runs.py # list_pipeline_runs(), get_pipeline_run()
      drones.py        # latest_telemetry_statement() (one row per drone_id,
                       # its greatest timestamp — shared with stats.py),
                       # _apply_filters() (shared WHERE-clause builder),
                       # list_drone_telemetry() (raw or latest-only, paginated
                       # or not), count_drone_telemetry(), list_drone_history(),
                       # get_drone_telemetry()
      stats.py         # get_stats(): fleet-wide summary built from
                       # latest_telemetry_statement() + one plain COUNT(*)

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
                     # GET /api/drones query parameters, including
                     # latest_only/page/page_size (Day 4). DroneTelemetryPage
                     # is the {items, total, page, page_size} envelope
                     # returned by GET /api/drones (Day 4). stats.py's
                     # StatsRead is the GET /api/stats response shape.
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
  date range — via a shared `_apply_filters()` helper, never filtering in
  Python after loading rows. Filters (plus `latest_only`/`page`/`page_size`,
  Day 4) are grouped into a `DroneTelemetryFilters` schema instance built by
  the route from individual FastAPI query parameters (kept as individual
  parameters, not a `Depends()`-injected query model, for straightforward
  alias handling of the `from`/`to` reserved-word parameter names). The
  public `?from=YYYY-MM-DD&to=YYYY-MM-DD` parameters are plain calendar
  dates; internally they become timezone-aware UTC boundaries:
  `timestamp >= start_of(from)` and `timestamp < start_of(to + 1 day)` — an
  exclusive upper bound, not a fragile `<= 23:59:59.999999` comparison.
  Returns a `DroneTelemetryPage` envelope: `{items, total, page, page_size}`
  (a deliberate, contained breaking change from the earlier bare-array
  response — see "Latest Position, Pagination and Stats (Day 4)" below for
  full details on `latest_only`, latest+filter semantics, and the
  pagination trade-off).
- `GET /api/drones/{drone_id}/history` (Day 4) —
  `services.drones.list_drone_history()`, oldest → newest, always
  **HTTP 200** (an unknown `drone_id` returns `200` + `[]`, never `404` —
  see below). `{drone_id}` is the *business* identifier (e.g.
  `"DRONE-001"`), unlike `{telemetry_id}` below.
- `GET /api/drones/{telemetry_id}` — `services.drones.get_drone_telemetry()`,
  **HTTP 404** if missing. `{telemetry_id}` is the `DroneTelemetry` row's own
  internal integer primary key (`id`), *not* the business `drone_id` — one
  `drone_id` can have many rows over time. No path conflict with the history
  route above: FastAPI/Starlette matches purely by path shape (one segment
  vs. two after `/api/drones/`), so declaration order doesn't matter here.
- `GET /api/stats` (Day 4) — `services.stats.get_stats()`, a whole-fleet
  summary, never affected by the query parameters `GET /api/drones` accepts
  (see below).

Invalid query parameter values (e.g. `min_battery=500`, an unknown
`status`, a non-integer path id, `page_size=101`) are rejected with
FastAPI/Pydantic's default **HTTP 422** — no custom validation/error
framework was added.

### Latest Position, Pagination and Stats (finalized in Day 4)

**Latest position per drone (`GET /api/drones?latest_only=true`)** — the map
always uses this mode; there is no user-facing "latest only" toggle.
`services.drones.latest_telemetry_statement()` builds one row per
`drone_id` — its single greatest-`timestamp` row — as a `MAX(timestamp)`
subquery grouped by `drone_id`, joined back onto `DroneTelemetry` on
`(drone_id, timestamp)`. No tiebreaker/window function is needed: that pair
is already unique (`uq_drone_telemetry_drone_id_timestamp`), so the join can
never return more than one row per drone. This same function is reused by
`services/stats.py` for every current-state stat, so there is exactly one
definition of "a drone's current state" in the codebase.

**Latest + filter semantics**: filters are applied *after* the latest-row
restriction, never before. Concretely, `_apply_filters()` runs against the
already-one-row-per-drone base query, so `status=lost_signal` only matches a
drone whose *current* status is `lost_signal` — a drone that was
`lost_signal` yesterday but is `active` now will not match, because its
older `lost_signal` row is never considered once a newer row exists for
that `drone_id`. The same logic applies to `min_battery` and the
`from`/`to` date range: a date range filter constrains the drone's own
*absolute latest* row's timestamp, never resurrecting an earlier row that
happens to fall inside the requested range.

**Pagination (`page`/`page_size`, default `1`/`20`, `page_size` capped at
`100`)** applies only when `latest_only=false` (the raw, un-collapsed
historical listing) — `OFFSET`/`LIMIT` plus a separate `COUNT(*)` query
(`count_drone_telemetry()`) populate the `total`/`page`/`page_size` envelope
fields. When `latest_only=true`, pagination is intentionally bypassed:
every matching drone's current row is returned in one implicit "page"
(`total = page_size = len(items)`), because that result set is bounded by
distinct-drone count (not telemetry history size), and the map needs the
complete current fleet at once. This is an explicit, documented trade-off:
historical telemetry can grow indefinitely (hence real pagination there),
while the "current fleet" view is small by nature at this exercise's scale.
A much larger production fleet might instead need viewport-based loading or
marker clustering on the frontend — not needed here.

**Path history (`GET /api/drones/{drone_id}/history`)** returns the full
recorded history for that `drone_id`, independent of any `GET /api/drones`
filter — selecting a drone on the map is a separate, deliberate user action,
and coupling its path to the currently-applied dashboard filters would be
surprising. Returns `200` + `[]` for an unknown `drone_id` rather than
`404`, because `drone_id` is a free-form column value being *filtered* on,
not a primary key being *looked up* — the same way the collection endpoint
responds to a filter that matches nothing.

**Stats (`GET /api/stats`)**: `total_telemetry_records` is a plain
`COUNT(*)` over the *entire* `drone_telemetry` table. Every other field
(`distinct_drones`, `active_drones`, `landed_drones`, `lost_signal_drones`,
`low_battery_drones`, `average_battery_percent`) is computed from
`latest_telemetry_statement()` only — i.e. each drone's current state, not
its full history. `low_battery_drones` uses the same strict `< 20` boundary
as the frontend's marker styling (`19` is low, `20` is not). Stats are
global and are never affected by the dashboard's filter panel — the route
takes no query parameters at all. The Angular dashboard does not currently
consume or display this endpoint; it exists as a backend API only.

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

Implemented layout (Angular 21, standalone components, zoneless, no
NgModules, no routing — a single dashboard page). File names follow
Angular's modern (2025-style) convention: no `.component`/`.service`
suffix on file names (e.g. `map-dashboard.ts`, `dashboard-state.ts`), while
class names keep a `Service` suffix only where that adds clarity
(`DronesApiService`, `PipelineApiService`, `DashboardStateService`).

```
frontend/
  src/
    app/
      core/
        api/
          api-config.ts        # API_BASE_URL constant (http://localhost:8000)
          drones-api.ts         # DronesApiService: listLatest() (GET /api/drones
                                 # with latest_only=true, Day 4), getHistory()
                                 # (GET /api/drones/{drone_id}/history, Day 4),
                                 # get() (GET /api/drones/{telemetry_id})
          pipeline-api.ts       # PipelineApiService: POST /api/pipeline/run,
                                 # GET /api/pipeline/runs[/:id]
          query-params.ts       # buildDroneQueryParams(): DroneFilters -> HttpParams
                                 # (omits empty/undefined fields; snake_case names)
          http-error.ts         # extractErrorMessage(): HttpErrorResponse -> string
        models/
          drone-telemetry.ts    # DroneTelemetry, DroneStatus (mirrors DroneTelemetryRead)
          drone-page.ts          # DronePage (mirrors DroneTelemetryPage envelope, Day 4)
          pipeline-run.ts       # PipelineRun, PipelineRunStatus (mirrors PipelineRunRead)
          drone-filters.ts      # DroneFilters (frontend-only filter shape, camelCase)
      features/
        map-dashboard/
          map-dashboard.ts       # MapDashboard: thin page/container, calls
                                  # DashboardStateService.loadInitial() on init
          dashboard-state.ts     # DashboardStateService: all dashboard state
                                  # (signals) + orchestration between the two
                                  # API services and the dashboard panels below
          filters/
            drone-filter-form.ts # DroneFilterForm: Reactive Form (drone type,
                                  # status, operator ID, min battery, from/to date)
          map/
            drone-map.ts          # DroneMap: Leaflet map lifecycle, CircleMarker
                                   # fleet markers (styled via marker-style.ts),
                                   # click-to-select, and a dedicated history
                                   # layer with a polyline plus small history-
                                   # point markers (Day 4)
            marker-style.ts        # getMarkerStyle(): pure function -> CircleMarker
                                    # options for normal / low-battery / lost-signal
            history-point-style.ts # getHistoryPointStyle(): small distinct markers
                                    # for each historical telemetry point (Day 4)
            history-render.ts      # getHistoricalPoints(), non-interactive overlay
                                    # options, and selected-history status messages
            history-map-view.ts    # computeHistoryMapView(): bounds vs single-point
                                    # center for framing a selected drone's path
            drone-popup.ts         # buildDronePopupHtml() (escaped, pure function)
            map-bounds.ts          # computeBounds() (pure function)
          pipeline-panel/
            pipeline-control.ts    # PipelineControl: "Run Pipeline" button
            pipeline-runs-table.ts # PipelineRunsTable: read-only run history table
      app.ts                  # Root component, renders <app-map-dashboard>
      app.config.ts           # provideBrowserGlobalErrorListeners(), provideHttpClient()
  public/
    leaflet/                  # Leaflet's layer-control images only (layers.png,
                               # layers-2x.png), copied from
                               # node_modules/leaflet/dist/images. The default
                               # marker-icon*.png/marker-shadow.png assets and the
                               # L.Icon.Default.mergeOptions() override were
                               # removed in Day 4 once every marker switched to
                               # L.circleMarker (no image assets needed).
```

### State Approach (implemented; extended Day 4)

- No NgRx. All dashboard state lives in `DashboardStateService` as
  **signals**: `drones`, `pipelineRuns`, `currentFilters`, `dronesLoading`,
  `pipelineRunsLoading`, `pipelineRunning`, `dronesError`, `pipelineError`,
  and (Day 4) `selectedDroneId`, `selectedDroneHistory`, `historyLoading`,
  `historyError` — each exposed read-only (`.asReadonly()`); only the
  service itself calls `.set()`.
- Components read these signals directly via `inject(DashboardStateService)`
  rather than through `@Input()` — there's exactly one dashboard instance, so
  prop-drilling would add indirection with no reuse benefit.
- Leaflet's `L.Map`/`L.LayerGroup`/`L.Polyline` objects and the Reactive
  Form's live control values are deliberately **not** signals — they're
  either mutable imperative objects Leaflet itself owns (kept local to
  `DroneMap`), or transient UI-only state that only matters at submit time.
- `drones` always holds the map's "one row per drone" current-fleet view
  (`DronesApiService.listLatest()`, which fixes `latest_only=true` — the
  dashboard has no user-facing toggle for this). `DroneMap` reads
  `state.drones()` inside an `effect()` to re-render `L.circleMarker`s
  whenever the list changes, instead of an `@Input()`.
- Filtering always goes through `GET /api/drones` — `DroneFilterForm` never
  filters an already-loaded array locally. Submitting calls
  `DashboardStateService.applyFilters(filters)`, which remembers the filter
  set and re-fetches; "Clear Filters" resets the form and calls
  `applyFilters({})`.
- **Drone selection / path history (Day 4)**: clicking a marker calls
  `DashboardStateService.selectDrone(droneId)`, which toggles selection off
  if that drone is already selected, or otherwise sets `selectedDroneId`,
  clears any previous history, and fetches
  `GET /api/drones/{drone_id}/history`. `DroneMap` reads
  `state.selectedDroneHistory()` inside a second `effect()` to redraw a
  dedicated history layer: small non-interactive history-point markers for
  every historical row *before* the latest one (via `getHistoricalPoints()`),
  plus a non-interactive `L.Polyline` through all coordinates when there are
  two or more points. The latest position is never duplicated as a history
  overlay — the interactive fleet marker remains the sole clickable marker
  at the drone's current position.
  `computeHistoryMapView()` — `fitBounds` for multi-point histories, or
  `setView` at a sensible fixed zoom for a single point. Every history
  request closes over the `droneId` it was made for; both its success and
  error callbacks re-check `this._selectedDroneId() === droneId` before
  applying anything. `refreshDrones()` also clears the current selection
  automatically if the selected drone is no longer present in a new
  (filtered) result.
- **`GET /api/stats` (backend only)**: the backend endpoint and its tests
  exist (Day 4), but the Angular dashboard does not call it or render a
  stats panel — the exercise only requires/proposes the API endpoint itself.
- `POST /api/pipeline/run` is still synchronous (no Celery yet): on *every*
  HTTP-level response (regardless of the run's own domain `status`),
  `DashboardStateService` refreshes drones and pipeline run history — the
  backend commits valid telemetry rows individually, so even a domain
  `"failed"` run may have persisted some rows before failing. On
  `status: "failed"`, `error_message` is also surfaced as `pipelineError`.
  An actual HTTP-level failure (network error, 500) is caught separately,
  refreshes nothing, and never crashes the dashboard.
- **Marker styling (Day 4)**: `getMarkerStyle(drone)` (`map/marker-style.ts`)
  is a pure function — no Leaflet dependency — returning `CircleMarker`
  options. Four states distinguished by color, fill, and a dashed outline
  for lost signal: normal (green), low battery only (`battery_percent < 20`,
  strictly — amber), lost signal only (`status === 'lost_signal'`, red with
  dashed outline), and both combined (dark red, dashed outline). All states
  share the same marker radius. A compact legend below the map reuses the
  same helper via `getMarkerLegendEntries()` so swatches stay in sync with
  live markers.

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

Everything below is Day 5 scope:

- Docker Compose file contents beyond PostgreSQL (`backend`, `worker`,
  `redis`, `frontend` services).
- Celery/Redis wiring details, async `POST /api/pipeline/run` (`HTTP 202` +
  `run_id`), and frontend polling of `GET /api/pipeline/runs/{run_id}`.
- Final README / setup instructions.

Day 4 (latest position per drone, drone path history, low-battery/
lost-signal marker styling, `GET /api/drones` pagination, `GET /api/stats`)
is finalized — see "Latest Position, Pagination and Stats (finalized in Day
4)" above and the "State Approach" section for the frontend side.

These remaining items are intentionally deferred per the agreed workflow:
implement only the phase that's explicitly requested.
