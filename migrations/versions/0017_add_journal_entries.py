"""create journal_entries table

Revision ID: 0017_add_journal_entries
Revises: 0016_add_reading_session_mode
Create Date: 2026-07-17 00:00:00.000000

KID-03 reading journal: a child's free-text/emoji/retelling response after a
book, more pedagogically valid than multiple-choice alone. See
jinbocho-docs/backlog/BACKLOG_KIDS_READING_EDUCATION.md.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017_add_journal_entries"
down_revision: Union[str, None] = "0016_add_reading_session_mode"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "journal_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owned_book_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("prompt_kind", sa.String(length=10), nullable=False, server_default="free"),
        sa.Column("emoji", sa.String(length=8), nullable=True),
        sa.Column("session_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("prompt_kind IN ('free','retelling','creative')", name="ck_journal_entries_prompt_kind"),
        sa.ForeignKeyConstraint(["owned_book_id"], ["owned_books.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["reading_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_journal_entries_owned_book_id"), "journal_entries", ["owned_book_id"], unique=False)
    op.create_index(op.f("ix_journal_entries_user_id"), "journal_entries", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_journal_entries_user_id"), table_name="journal_entries")
    op.drop_index(op.f("ix_journal_entries_owned_book_id"), table_name="journal_entries")
    op.drop_table("journal_entries")
