"""PipelineRun ORM model — one row per pipeline execution (history + counters).

Deliberately independent from DroneTelemetry: no foreign key or SQLAlchemy
relationship. The exercise requires pipeline execution history, not
per-record ingestion lineage, so keeping the two tables unrelated is the
simpler design (see the Phase 1C design plan / ARCHITECTURE.md). A nullable
link could be added later without touching this table if that ever becomes
a real requirement.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import PipelineRunStatus, pipeline_run_status_type


class PipelineRun(Base):
    __tablename__ = "pipeline_run"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Set explicitly by the pipeline runner when a run starts — not a
    # DB-side default, since it's a business timestamp the runner controls.
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    status: Mapped[PipelineRunStatus] = mapped_column(
        pipeline_run_status_type,
        nullable=False,
        default=PipelineRunStatus.QUEUED,
        server_default=PipelineRunStatus.QUEUED.value,
    )

    total_records: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    valid_records: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    invalid_records: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    duplicate_records: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Logical filename selected for this run (not an absolute path).
    input_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
