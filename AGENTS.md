# Agent Instructions — Drone Activity Map Dashboard

These are working rules for any AI coding agent (or human) contributing to
this repository. Read [`PROJECT_CONTEXT.md`](./PROJECT_CONTEXT.md) and
[`ARCHITECTURE.md`](./ARCHITECTURE.md) first — this file governs *how* to
work, those govern *what* to build.

## Workflow Rules

1. **Work only on the phase explicitly requested.** Do not jump ahead to
   implement later phases (e.g. don't add Celery/Redis/Docker Compose or
   bonus UI highlighting unless specifically asked, even if it seems like a
   natural next step).
2. **Before a significant multi-file change**, briefly state which files you
   intend to create/change and why, before making the change.
3. **After each implementation step**, summarize:
   1. Files created/changed.
   2. Responsibility of each file.
   3. Important architectural decisions made.
   4. Commands to run to verify the result (install, migrate, run, test).
4. **Do not silently redesign existing architecture.** If you believe an
   existing decision documented in `ARCHITECTURE.md` or
   `PROJECT_CONTEXT.md` should change, say so explicitly and ask/confirm
   before doing it — don't just change it while implementing something else.
5. **Do not fix unrelated code while implementing a task.** If you notice an
   unrelated issue, mention it, but don't fix it as a drive-by change.
6. **Do not implement bonus features until explicitly requested.** Avoid
   architectural choices that would block them later (see "Future Bonus
   Preparation" in `PROJECT_CONTEXT.md`).

## Non-Negotiable Architectural Constraints

- The core pipeline runner (`backend/app/pipeline/...`) must **not** import
  or depend on FastAPI or Celery. It must be callable as plain Python from
  anywhere (API route, Celery task, script, test).
- All telemetry records must be stored — never overwrite/upsert to
  "latest only". Latest-position and path-history views/queries are derived
  from the full history table.
- Invalid individual records are skipped and counted; a few bad records must
  never fail an entire pipeline run.
- Persistence goes through SQLAlchemy models/repositories — no other part of
  the codebase should construct raw SQL or bypass this layer.
- Frontend: standalone Angular components only (no NgModules), no NgRx, no
  UI framework (e.g. Angular Material) unless explicitly requested later.

## Technology Stack (fixed, do not swap without explicit request)

**Frontend:** Angular 21, standalone architecture, Leaflet, Angular services
+ signals, Reactive Forms where appropriate.

**Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL, Alembic, Pydantic.

**Pipeline input:** JSON file (initial source).

**Deferred / out of scope:** Redis persistence, advanced Celery retry
infrastructure, Flower monitoring, reverse proxy, expanded test coverage
beyond what the project already includes.

## Code Quality Expectations

- Keep the architecture simple and readable; avoid over-engineering.
- Clear separation of concerns: API layer, business/pipeline logic,
  persistence — each in its own module, per `ARCHITECTURE.md`.
- Don't introduce a technology, library, or pattern that isn't needed for
  the current phase.
- Write code that's easy to follow for an experienced Java/TypeScript
  developer who is newer to Python — favor explicitness and standard
  library/framework idioms over clever or implicit Python-isms.

## Local Environment Notes

Docker Compose is the recommended evaluator path (`docker compose up --build`).
For local Python development without containers, ensure PostgreSQL is running
(for example via the Compose `db` service) and copy `backend/.env.example` to
`backend/.env`.

- Python on this machine is a very recent version; if any backend dependency
  lacks a pre-built wheel for it, prefer using the `psycopg` (v3) PostgreSQL
  driver over `psycopg2`, and flag any install friction rather than silently
  downgrading Python.
