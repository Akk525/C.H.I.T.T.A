"""init postgis models

Revision ID: 0001_init
Revises: 
Create Date: 2026-06-02 19:40:52.607572

"""
from typing import Sequence, Union

from alembic import op
from geoalchemy2 import Geometry
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001_init'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    op.create_table(
        "sites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("geom", Geometry("POINT", srid=4326), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "site_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("site_analyses")
    op.drop_table("sites")
