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
from app.schemas.drone_telemetry import DroneTelemetryFilters, DroneTelemetryRead
from app.services import drones as drones_service

router = APIRouter(tags=["drones"])


@router.get("/api/drones", response_model=list[DroneTelemetryRead])
def list_drones(
    drone_type: str | None = None,
    status: DroneStatus | None = None,
    operator_id: str | None = None,
    min_battery: int | None = Query(default=None, ge=0, le=100),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
) -> list[DroneTelemetryRead]:
    """Telemetry records matching every provided (optional) filter.

    Returns individual telemetry rows, not "latest position per drone" —
    that is a separate, not-yet-implemented feature. `from`/`to` are plain
    calendar dates (YYYY-MM-DD); see app/services/drones.py for how they
    are turned into timezone-aware boundaries.
    """
    filters = DroneTelemetryFilters(
        drone_type=drone_type,
        status=status,
        operator_id=operator_id,
        min_battery=min_battery,
        date_from=date_from,
        date_to=date_to,
    )
    records = drones_service.list_drone_telemetry(db, filters)
    return [DroneTelemetryRead.model_validate(record) for record in records]


@router.get("/api/drones/{telemetry_id}", response_model=DroneTelemetryRead)
def get_drone(telemetry_id: int, db: Session = Depends(get_db)) -> DroneTelemetryRead:
    """Look up one telemetry row by its internal integer primary key.

    `{telemetry_id}` is the `DroneTelemetry` row's own `id`, not the
    business `drone_id` (which can have many rows over time). A future
    business-drone history endpoint is expected to live at a separate route
    such as `/api/drones/{drone_id}/history` instead of overloading this one.
    """
    record = drones_service.get_drone_telemetry(db, telemetry_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Drone telemetry record {telemetry_id} not found")
    return DroneTelemetryRead.model_validate(record)
