"""Pydantic response schema for `GET /api/stats`.

See app/services/stats.py for exactly which fields are computed from full
telemetry history vs. each drone's latest row only.
"""

from pydantic import BaseModel


class StatsRead(BaseModel):
    total_telemetry_records: int
    distinct_drones: int
    active_drones: int
    landed_drones: int
    lost_signal_drones: int
    low_battery_drones: int
    average_battery_percent: float | None
