"""Fleet-wide summary statistics for `GET /api/stats`.

Every "current state" field (everything except `total_telemetry_records`)
is computed from each drone's own latest telemetry row
(`app.services.drones.latest_telemetry_statement()`), not from raw
history — a drone that was `lost_signal` yesterday but is `active` now
counts only as active. These stats are global fleet numbers and are never
affected by the dashboard's filter panel.
"""

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.drone_telemetry import DroneTelemetry
from app.models.enums import DroneStatus
from app.schemas.stats import StatsRead
from app.services.drones import latest_telemetry_statement


def get_stats(db: Session) -> StatsRead:
    total_telemetry_records = db.execute(select(func.count()).select_from(DroneTelemetry)).scalar_one()

    latest = latest_telemetry_statement().subquery()

    row = db.execute(
        select(
            func.count().label("distinct_drones"),
            func.sum(case((latest.c.status == DroneStatus.ACTIVE, 1), else_=0)).label("active_drones"),
            func.sum(case((latest.c.status == DroneStatus.LANDED, 1), else_=0)).label("landed_drones"),
            func.sum(case((latest.c.status == DroneStatus.LOST_SIGNAL, 1), else_=0)).label(
                "lost_signal_drones"
            ),
            func.sum(case((latest.c.battery_percent < 20, 1), else_=0)).label("low_battery_drones"),
            func.avg(latest.c.battery_percent).label("average_battery_percent"),
        ).select_from(latest)
    ).one()

    average_battery_percent = (
        round(float(row.average_battery_percent), 1) if row.average_battery_percent is not None else None
    )

    return StatsRead(
        total_telemetry_records=total_telemetry_records,
        distinct_drones=row.distinct_drones or 0,
        active_drones=row.active_drones or 0,
        landed_drones=row.landed_drones or 0,
        lost_signal_drones=row.lost_signal_drones or 0,
        low_battery_drones=row.low_battery_drones or 0,
        average_battery_percent=average_battery_percent,
    )
