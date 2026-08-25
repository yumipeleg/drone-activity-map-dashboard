"""Shared Python enums for the two controlled status sets in the schema.

Both are persisted as their string VALUE (e.g. "lost_signal"), not the
Python member NAME (e.g. "LOST_SIGNAL") — enforced explicitly via
`values_callable` below, since SQLAlchemy's default behavior for a
Python `Enum` column is to store/compare the member NAME. Each column type
is also given a stable, explicit name so the CHECK constraint Alembic
generates has a readable, predictable name instead of an auto-generated one.

Native PostgreSQL enum types (`CREATE TYPE ... AS ENUM`) were deliberately
not used — see the Phase 1C design plan / ARCHITECTURE.md for the
comparison. A plain string column with an explicit CHECK constraint is
simpler to read, migrate, and test.
"""

from enum import Enum

from sqlalchemy import Enum as SqlEnum


class DroneStatus(str, Enum):
    ACTIVE = "active"
    LANDED = "landed"
    LOST_SIGNAL = "lost_signal"


class PipelineRunStatus(str, Enum):
    QUEUED = "queued"
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


def _persist_enum_values(enum_cls: type[Enum]) -> list[str]:
    """Make SQLAlchemy store/compare each member's VALUE, not its NAME."""
    return [member.value for member in enum_cls]


# native_enum=False -> plain VARCHAR column instead of a PostgreSQL ENUM type.
# create_constraint=True -> explicitly request the CHECK constraint (this
#   does NOT happen automatically for non-native enums on every SQLAlchemy
#   version, so it is set here rather than relied upon implicitly).
drone_status_type = SqlEnum(
    DroneStatus,
    name="drone_status",
    native_enum=False,
    create_constraint=True,
    values_callable=_persist_enum_values,
    length=20,
)

pipeline_run_status_type = SqlEnum(
    PipelineRunStatus,
    name="pipeline_run_status",
    native_enum=False,
    create_constraint=True,
    values_callable=_persist_enum_values,
    length=20,
)
