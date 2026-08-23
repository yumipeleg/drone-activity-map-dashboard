"""Focused tests for DroneTelemetryInput — validation and normalization
behavior. Pure Pydantic, no database involved.
"""

import pytest
from pydantic import ValidationError

from app.schemas.drone_telemetry import DroneTelemetryInput

VALID_RECORD = {
    "drone_id": "DRONE-001",
    "drone_type": "Quadcopter",
    "operator_id": "OP-123",
    "latitude": 32.0853,
    "longitude": 34.7818,
    "altitude_m": 120,
    "speed_kmh": 45,
    "battery_percent": 76,
    "timestamp": "2026-06-28T10:30:00Z",
    "status": "active",
}


def test_valid_record_is_accepted_and_normalized() -> None:
    record = DroneTelemetryInput.model_validate(
        {**VALID_RECORD, "drone_id": "  DRONE-001  ", "status": " Active "}
    )

    assert record.drone_id == "DRONE-001"
    assert record.status.value == "active"
    assert record.timestamp.tzinfo is not None


def test_empty_drone_id_is_rejected() -> None:
    with pytest.raises(ValidationError):
        DroneTelemetryInput.model_validate({**VALID_RECORD, "drone_id": "   "})


def test_latitude_out_of_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        DroneTelemetryInput.model_validate({**VALID_RECORD, "latitude": 200})


def test_longitude_out_of_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        DroneTelemetryInput.model_validate({**VALID_RECORD, "longitude": -200})


def test_negative_altitude_is_rejected() -> None:
    with pytest.raises(ValidationError):
        DroneTelemetryInput.model_validate({**VALID_RECORD, "altitude_m": -50})


def test_battery_percent_out_of_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        DroneTelemetryInput.model_validate({**VALID_RECORD, "battery_percent": 150})


def test_invalid_timestamp_is_rejected() -> None:
    with pytest.raises(ValidationError):
        DroneTelemetryInput.model_validate({**VALID_RECORD, "timestamp": "invalid-date"})


def test_unknown_status_is_rejected() -> None:
    with pytest.raises(ValidationError):
        DroneTelemetryInput.model_validate({**VALID_RECORD, "status": "flying"})
