"""create reading_paths table

Revision ID: 0018_add_reading_paths
Revises: 0017_add_journal_entries
Create Date: 2026-07-17 00:00:00.000000

KID-06 reading paths: an ordered, themed sequence of books from the
family's own catalog. Completion is derived client-side from BookRead, same
as the KID-10 portfolio — this table only stores the path definition. See
jinbocho-docs/backlog/BACKLOG_KIDS_READING_EDUCATION.md.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018_add_reading_paths"
down_revision: Union[str, None] = "0017_add_journal_entries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reading_paths",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("library_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("book_ids", postgresql.ARRAY(sa.UUID()), nullable=False),
        sa.Column("target_band", sa.String(length=10), nullable=True),
        sa.Column("source", sa.String(length=10), nullable=False, server_default="manual"),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("source IN ('manual','ai')", name="ck_reading_paths_source"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reading_paths_library_id"), "reading_paths", ["library_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reading_paths_library_id"), table_name="reading_paths")
    op.drop_table("reading_paths")
