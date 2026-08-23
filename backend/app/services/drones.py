"""Query operations for `DroneTelemetry`.

Filtering happens entirely in SQL (SQLAlchemy `.filter()` calls building
one query), never by loading rows into Python and filtering there — see
`list_drone_telemetry` below.
"""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.drone_telemetry import DroneTelemetry
from app.schemas.drone_telemetry import DroneTelemetryFilters


def list_drone_telemetry(db: Session, filters: DroneTelemetryFilters) -> list[DroneTelemetry]:
    """All telemetry rows matching every provided (optional) filter.

    Returns raw telemetry records, most recent first — not "latest position
    per drone"; that is a separate, not-yet-implemented feature.
    """
    statement = select(DroneTelemetry)

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

    statement = statement.order_by(DroneTelemetry.timestamp.desc())
    return list(db.execute(statement).scalars().all())


def get_drone_telemetry(db: Session, telemetry_id: int) -> DroneTelemetry | None:
    """Look up one telemetry row by its internal integer primary key.

    Not `drone_id` — a business drone identifier can have many rows. See
    app/api/routes/drones.py for the route-level clarification.
    """
    return db.get(DroneTelemetry, telemetry_id)


def _start_of_day_utc(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=timezone.utc)
