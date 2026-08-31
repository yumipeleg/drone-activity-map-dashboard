"""add input_file to pipeline_run

Revision ID: c3d9a2f18e04
Revises: b8c2e1f04a9d
Create Date: 2026-08-31 11:36:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c3d9a2f18e04"
down_revision: Union[str, Sequence[str], None] = "b8c2e1f04a9d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pipeline_run",
        sa.Column("input_file", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pipeline_run", "input_file")
