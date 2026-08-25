"""add queued pipeline run status

Revision ID: b8c2e1f04a9d
Revises: 4fb3a7ad895f
Create Date: 2026-08-25 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b8c2e1f04a9d"
down_revision: Union[str, Sequence[str], None] = "4fb3a7ad895f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Inspected from the development database (pg_constraint on pipeline_run):
#   pipeline_run_status | CHECK (status IN ('started', 'completed', 'failed'))
_STATUS_CHECK = "pipeline_run_status"


def upgrade() -> None:
    op.drop_constraint(_STATUS_CHECK, "pipeline_run", type_="check")
    op.create_check_constraint(
        _STATUS_CHECK,
        "pipeline_run",
        "status IN ('queued', 'started', 'completed', 'failed')",
    )
    op.alter_column("pipeline_run", "status", server_default="queued")


def downgrade() -> None:
    # Downgrade requires no rows with status='queued' to exist.
    op.drop_constraint(_STATUS_CHECK, "pipeline_run", type_="check")
    op.create_check_constraint(
        _STATUS_CHECK,
        "pipeline_run",
        "status IN ('started', 'completed', 'failed')",
    )
    op.alter_column("pipeline_run", "status", server_default="started")
