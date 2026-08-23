"""DroneTelemetry ORM model — one row per ingested telemetry event.

The same drone_id can have many rows over time (full history is kept, not
just the latest position — see ARCHITECTURE.md). `(drone_id, timestamp)` is
the duplicate-event identity rule: re-running the same input file is safe
because that pair is unique, so an already-stored event is skipped rather
than inserted twice.

Business range validation (lat/long bounds, battery 0-100, etc.) is
deliberately NOT enforced here — that belongs to the later Pydantic/pipeline
validation layer, per EXERCISE.md's validation rules and AGENTS.md.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import DroneStatus, drone_status_type


class DroneTelemetry(Base):
    __tablename__ = "drone_telemetry"
    __table_args__ = (
        UniqueConstraint(
            "drone_id", "timestamp", name="uq_drone_telemetry_drone_id_timestamp"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    drone_id: Mapped[str] = mapped_column(String(64), nullable=False)
    drone_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    operator_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    altitude_m: Mapped[float] = mapped_column(Float, nullable=False)
    speed_kmh: Mapped[float] = mapped_column(Float, nullable=False)
    battery_percent: Mapped[int] = mapped_column(Integer, nullable=False)

    # Event time reported by the drone itself (timezone-aware).
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    status: Mapped[DroneStatus] = mapped_column(
        drone_status_type, nullable=False, index=True
    )

    # Row-insertion bookkeeping — distinct from `timestamp` (the event time).
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
