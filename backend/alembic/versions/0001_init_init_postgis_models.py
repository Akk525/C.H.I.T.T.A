"""init postgis models

Revision ID: 0001_init
Revises:
Create Date: 2026-06-02 19:40:52.607572

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001_init'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. PostGIS is optional — uses TEXT fallback if not installed."""
    bind = op.get_bind()

    # Use a SAVEPOINT so a PostGIS failure doesn't abort the whole transaction
    has_postgis = False
    bind.execute(sa.text("SAVEPOINT postgis_attempt"))
    try:
        bind.execute(sa.text("CREATE EXTENSION IF NOT EXISTS postgis"))
        has_postgis = True
        bind.execute(sa.text("RELEASE SAVEPOINT postgis_attempt"))
    except Exception:
        bind.execute(sa.text("ROLLBACK TO SAVEPOINT postgis_attempt"))
        bind.execute(sa.text("RELEASE SAVEPOINT postgis_attempt"))

    cols = [
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]
    if has_postgis:
        from geoalchemy2 import Geometry
        cols.insert(3, sa.Column("geom", Geometry("POINT", srid=4326), nullable=False))
    else:
        cols.insert(3, sa.Column("geom", sa.Text(), nullable=True))

    op.create_table("sites", *cols)

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
