"""Routes for querying drone telemetry records.

Thin by design: all filtering/querying is delegated to
app/services/drones.py. This module only collects and forwards query
parameters.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.enums import DroneStatus
from app.schemas.drone_telemetry import DroneTelemetryFilters, DroneTelemetryPage, DroneTelemetryRead
from app.services import drones as drones_service

router = APIRouter(tags=["drones"])


@router.get("/api/drones", response_model=DroneTelemetryPage)
def list_drones(
    drone_type: str | None = None,
    status: DroneStatus | None = None,
    operator_id: str | None = None,
    min_battery: int | None = Query(default=None, ge=0, le=100),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    latest_only: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> DroneTelemetryPage:
    """Telemetry records matching every provided (optional) filter.

    `latest_only=true` restricts results to one row per drone — its own
    current/latest telemetry event — with every filter then applied to
    THAT row: a drone that was `lost_signal` yesterday but is `active` now
    will not match `status=lost_signal` (see PROJECT_CONTEXT.md's latest +
    filter semantics). `from`/`to` are plain calendar dates (YYYY-MM-DD);
    under `latest_only`, they constrain the drone's own latest row's
    timestamp, not any earlier historical row.

    Pagination (`page`/`page_size`) applies only when `latest_only=false`.
    A `latest_only=true` request always returns every matching drone
    regardless of `page`/`page_size` — the map needs the complete current
    fleet at once, and that result set is bounded by distinct-drone count,
    not telemetry history size (see `DroneTelemetryPage`).
    """
    filters = DroneTelemetryFilters(
        drone_type=drone_type,
        status=status,
        operator_id=operator_id,
        min_battery=min_battery,
        date_from=date_from,
        date_to=date_to,
        latest_only=latest_only,
        page=page,
        page_size=page_size,
    )
    records = drones_service.list_drone_telemetry(db, filters)
    items = [DroneTelemetryRead.model_validate(record) for record in records]

    if filters.latest_only:
        return DroneTelemetryPage(items=items, total=len(items), page=1, page_size=len(items))

    total = drones_service.count_drone_telemetry(db, filters)
    return DroneTelemetryPage(items=items, total=total, page=filters.page, page_size=filters.page_size)


@router.get("/api/drones/{drone_id}/history", response_model=list[DroneTelemetryRead])
def get_drone_history(drone_id: str, db: Session = Depends(get_db)) -> list[DroneTelemetryRead]:
    """Every telemetry row for one business `drone_id`, oldest first.

    `{drone_id}` is the business identifier (e.g. "DRONE-001"), unlike
    `GET /api/drones/{telemetry_id}` below, which is the internal row's
    own primary key. Returns `200` + `[]` for an unknown/never-seen
    `drone_id` rather than `404`: `drone_id` is a free-form column value,
    not a looked-up primary key, so "no rows" is the natural response —
    the same way the collection endpoint above responds to a filter that
    matches nothing. Always the full recorded history, independent of any
    dashboard filter (selecting a drone is a separate, deliberate action).
    """
    records = drones_service.list_drone_history(db, drone_id)
    return [DroneTelemetryRead.model_validate(record) for record in records]


@router.get("/api/drones/{telemetry_id}", response_model=DroneTelemetryRead)
def get_drone(telemetry_id: int, db: Session = Depends(get_db)) -> DroneTelemetryRead:
    """Look up one telemetry row by its internal integer primary key.

    `{telemetry_id}` is the `DroneTelemetry` row's own `id`, not the
    business `drone_id` (which can have many rows over time) — see
    `GET /api/drones/{drone_id}/history` above for that.
    """
    record = drones_service.get_drone_telemetry(db, telemetry_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Drone telemetry record {telemetry_id} not found")
    return DroneTelemetryRead.model_validate(record)
