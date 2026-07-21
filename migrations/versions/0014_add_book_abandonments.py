"""create book_abandonments table

Revision ID: 0014_add_book_abandonments
Revises: 0013_add_quiz_tables
Create Date: 2026-07-17 00:00:00.000000

Mirrors book_reads (see 0004) — one row per (owned_book_id, user_id), mutually
exclusive with a BookRead row for the same pair. Never touches
owned_books.reading_status (a native pg enum restricted to to_read/reading):
"abandoned" is a per-viewer computed status, same as "read" already is. See
KID-05 in jinbocho-docs/backlog/BACKLOG_KIDS_READING_EDUCATION.md.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0014_add_book_abandonments"
down_revision = "0013_add_quiz_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "book_abandonments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "owned_book_id",
            UUID(as_uuid=True),
            sa.ForeignKey("owned_books.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # No FK: users live in the auth service's database.
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("abandoned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("owned_book_id", "user_id", name="uq_book_abandonments_book_user"),
    )
    op.create_index("ix_book_abandonments_owned_book_id", "book_abandonments", ["owned_book_id"])
    op.create_index("ix_book_abandonments_user_id", "book_abandonments", ["user_id"])


def downgrade() -> None:
    op.drop_table("book_abandonments")
