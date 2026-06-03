"""add saved_runs table

Revision ID: 0002_saved_runs
Revises: 0001_init
Create Date: 2026-06-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID


revision: str = '0002_saved_runs'
down_revision: Union[str, Sequence[str], None] = '0001_init'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "saved_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("run_type", sa.String(32), nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("region_name", sa.String(255), nullable=True),
        sa.Column("total_suitability_score", sa.Float(), nullable=True),
        sa.Column("final_decision", sa.String(32), nullable=True),
        sa.Column("formula_version", sa.String(32), nullable=True),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "tags",
            ARRAY(sa.String),
            nullable=False,
            server_default="{}",
        ),
    )
    op.create_index(
        "ix_saved_runs_type_created",
        "saved_runs",
        ["run_type", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_saved_runs_type_created")
    op.drop_table("saved_runs")
