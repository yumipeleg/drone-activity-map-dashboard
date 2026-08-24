"""Query operations for `DroneTelemetry`.

Filtering happens entirely in SQL (SQLAlchemy `.where()` calls building one
query), never by loading rows into Python and filtering there.
"""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.drone_telemetry import DroneTelemetry
from app.schemas.drone_telemetry import DroneTelemetryFilters


def latest_telemetry_statement() -> Select:
    """One row per `drone_id`: that drone's single greatest-`timestamp` row.

    Built as a `MAX(timestamp)` grouped subquery joined back onto
    `DroneTelemetry` on `(drone_id, timestamp)` — safe with no tiebreaker
    needed because that pair is already unique
    (`uq_drone_telemetry_drone_id_timestamp`), so this join can never
    return more than one row per drone. Shared by the `latest_only=true`
    listing mode below and by `app/services/stats.py`'s current-state
    fields, so there is exactly one definition of "a drone's current
    state" in the codebase.
    """
    latest = (
        select(
            DroneTelemetry.drone_id.label("drone_id"),
            func.max(DroneTelemetry.timestamp).label("max_timestamp"),
        )
        .group_by(DroneTelemetry.drone_id)
        .subquery()
    )
    return select(DroneTelemetry).join(
        latest,
        (DroneTelemetry.drone_id == latest.c.drone_id)
        & (DroneTelemetry.timestamp == latest.c.max_timestamp),
    )


def _apply_filters(statement: Select, filters: DroneTelemetryFilters) -> Select:
    """Adds one `.where()` per provided (optional) filter.

    Shared by every listing/counting mode. When `filters.latest_only` is
    set, the caller has already restricted `statement` to one row per
    drone (see `latest_telemetry_statement`) *before* this runs — so e.g.
    `status=lost_signal` only matches a drone whose CURRENT status is
    lost_signal, never an older historical row that happened to match
    (see PROJECT_CONTEXT.md's latest + filter semantics).
    """
    if filters.drone_type is not None:
        statement = statement.where(DroneTelemetry.drone_type == filters.drone_type)
    if filters.status is not None:
        statement = statement.where(DroneTelemetry.status == filters.status)
    if filters.operator_id is not None:
        statement = statement.where(DroneTelemetry.operator_id == filters.operator_id)
    if filters.min_battery is not None:
        statement = statement.where(DroneTelemetry.battery_percent >= filters.min_battery)
    if filters.date_from is not None:
        statement = statement.where(DroneTelemetry.timestamp >= _start_of_day_utc(filters.date_from))
    if filters.date_to is not None:
        # Exclusive upper bound: "to" means up to (but not including) the
        # start of the *following* day, so a full day is included without
        # relying on a fragile end-of-day timestamp like 23:59:59.999999.
        statement = statement.where(
            DroneTelemetry.timestamp < _start_of_day_utc(filters.date_to + timedelta(days=1))
        )
    return statement


def _base_statement(filters: DroneTelemetryFilters) -> Select:
    return latest_telemetry_statement() if filters.latest_only else select(DroneTelemetry)


def list_drone_telemetry(db: Session, filters: DroneTelemetryFilters) -> list[DroneTelemetry]:
    """Telemetry rows matching every provided (optional) filter, most recent first.

    `filters.latest_only=True` restricts the base set to one row per drone
    (its own current state) before filters are applied — see
    `_apply_filters`. Pagination (`filters.page`/`page_size`) is applied
    only when `latest_only` is False: that mode is inherently bounded by
    the number of distinct drones (not the size of telemetry history), and
    the map that consumes it needs every matching drone's current position
    at once, not one page of them.
    """
    statement = _apply_filters(_base_statement(filters), filters)
    statement = statement.order_by(DroneTelemetry.timestamp.desc())

    if not filters.latest_only:
        statement = statement.offset((filters.page - 1) * filters.page_size).limit(filters.page_size)

    return list(db.execute(statement).scalars().all())


def count_drone_telemetry(db: Session, filters: DroneTelemetryFilters) -> int:
    """Total rows matching every provided filter, ignoring pagination.

    Used to populate `DroneTelemetryPage.total`. Not called for
    `latest_only` listings (see `list_drone_telemetry`'s route caller) —
    that mode always returns its full matching set, so `len(items)` is
    already the total.
    """
    statement = _apply_filters(_base_statement(filters), filters)
    return db.execute(select(func.count()).select_from(statement.subquery())).scalar_one()


def list_drone_history(db: Session, drone_id: str) -> list[DroneTelemetry]:
    """Every telemetry row for one business `drone_id`, oldest first.

    This is the full recorded path for that drone, independent of any
    dashboard filter — see app/api/routes/drones.py's history route.
    """
    statement = (
        select(DroneTelemetry)
        .where(DroneTelemetry.drone_id == drone_id)
        .order_by(DroneTelemetry.timestamp.asc())
    )
    return list(db.execute(statement).scalars().all())


def get_drone_telemetry(db: Session, telemetry_id: int) -> DroneTelemetry | None:
    """Look up one telemetry row by its internal integer primary key.

    Not `drone_id` — a business drone identifier can have many rows. See
    app/api/routes/drones.py for the route-level clarification.
    """
    return db.get(DroneTelemetry, telemetry_id)


def _start_of_day_utc(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=timezone.utc)
