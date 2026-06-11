"""add incipit columns to bibliographic_records

Revision ID: 0007_add_incipit
Revises: 0006_add_genre_raw_and_normalize
Create Date: 2026-06-11 00:00:01.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0007_add_incipit"
down_revision = "0006_add_genre_raw_and_normalize"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bibliographic_records", sa.Column("incipit", sa.Text(), nullable=True))
    op.add_column("bibliographic_records", sa.Column("incipit_source", sa.String(20), nullable=True))
    op.add_column(
        "bibliographic_records",
        sa.Column("incipit_generated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bibliographic_records", "incipit_generated_at")
    op.drop_column("bibliographic_records", "incipit_source")
    op.drop_column("bibliographic_records", "incipit")
