"""Pydantic response schema for a `PipelineRun`.

Used for all three "PipelineRun-shaped" API responses: `GET
/api/pipeline/runs`, `GET /api/pipeline/runs/{id}`, and `POST
/api/pipeline/run` — see app/api/routes/pipeline.py for why the POST route
re-fetches the row instead of mapping `PipelineResult` directly.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import PipelineRunStatus


class PipelineRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    finished_at: datetime | None
    status: PipelineRunStatus
    total_records: int
    valid_records: int
    invalid_records: int
    duplicate_records: int
    error_message: str | None
