"""Pydantic v2 schema for a single raw drone telemetry record.

Validates and conservatively normalizes one record from the pipeline's
input source, per the rules in EXERCISE.md. Reuses `DroneStatus` from the
SQLAlchemy models (app/models/enums.py) so there is exactly one definition
of the allowed status values shared by the database and the pipeline/API
layers.

Normalization lives here (not in a separate normalizer module): whitespace
trimming and status-casing are handled by Pydantic's own `mode="before"`
hooks / model config, which run before the corresponding field's type or
range check — so "normalize then validate" holds conceptually even though
it happens inside one call to `model_validate()`.
"""

from datetime import date, datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import DroneStatus


class DroneTelemetryInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    drone_id: str = Field(min_length=1)
    drone_type: str
    operator_id: str

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    altitude_m: float = Field(ge=0)
    speed_kmh: float
    battery_percent: int = Field(ge=0, le=100)

    timestamp: datetime
    status: DroneStatus

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status_casing(cls, value: object) -> object:
        """Allow safe casing/whitespace variants, e.g. " Active " -> "active".

        This only reshapes text — a genuinely unknown value like "flying"
        still fails validation afterward, it is never guessed or repaired.
        """
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("timestamp", mode="after")
    @classmethod
    def default_naive_timestamps_to_utc(cls, value: datetime) -> datetime:
        """Assume UTC for a timestamp with no offset.

        Assumption: EXERCISE.md only requires "a valid date/time value" and
        does not define a policy for a missing UTC offset. The exercise's
        own sample data always includes "Z", so this mainly matters for
        hand-edited test/demo records.
        """
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class DroneTelemetryRead(BaseModel):
    """API response shape for one stored `DroneTelemetry` row.

    Separate from `DroneTelemetryInput` on purpose: that schema validates
    raw pipeline input, while this one describes what the API returns
    (includes `id` and `created_at`, which the input never has).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    drone_id: str
    drone_type: str
    operator_id: str
    latitude: float
    longitude: float
    altitude_m: float
    speed_kmh: float
    battery_percent: int
    timestamp: datetime
    status: DroneStatus
    created_at: datetime


class DroneTelemetryFilters(BaseModel):
    """Internal DTO grouping the already-validated `GET /api/drones` query
    parameters, so the route stays a thin pass-through and the service
    function has one clear object to build a query from (rather than nine
    loose positional/keyword arguments).

    `latest_only`/`page`/`page_size` are not "filters" in the WHERE-clause
    sense, but grouping them here keeps the route/service boundary at one
    object either way — see app/services/drones.py for how each is used.
    """

    drone_type: str | None = None
    status: DroneStatus | None = None
    operator_id: str | None = None
    min_battery: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    latest_only: bool = False
    page: int = 1
    page_size: int = 20


class DroneTelemetryPage(BaseModel):
    """Paginated envelope returned by `GET /api/drones`.

    For a `latest_only=true` request, pagination is bypassed (see
    app/services/drones.py and app/api/routes/drones.py): `items` contains
    every matching drone's current row, and `total`/`page_size` both equal
    `len(items)` — the map needs the complete current fleet at once, and
    that result set is bounded by distinct-drone count, not telemetry
    history size. A production fleet at much larger scale might instead
    need viewport-based loading or marker clustering; not needed here.
    """

    items: list[DroneTelemetryRead]
    total: int
    page: int
    page_size: int
