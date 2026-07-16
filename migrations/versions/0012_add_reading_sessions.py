"""add reading_sessions table

Revision ID: 0012_add_reading_sessions
Revises: 0011_add_book_loan_borrower_user
Create Date: 2026-07-16 00:00:00.000000

New table for Kids Mode: a child logs their own reading sessions
(minutes and/or pages) against a book they own. No FK on user_id — catalog_db
and auth_db are separate databases (ADR-007), same pattern as book_reads and
owned_books.owner_id.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_add_reading_sessions"
down_revision: Union[str, None] = "0011_add_book_loan_borrower_user"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reading_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owned_book_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=True),
        sa.Column("pages", sa.Integer(), nullable=True),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("minutes IS NOT NULL OR pages IS NOT NULL", name="ck_reading_sessions_minutes_or_pages"),
        sa.ForeignKeyConstraint(["owned_book_id"], ["owned_books.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reading_sessions_owned_book_id"), "reading_sessions", ["owned_book_id"], unique=False)
    op.create_index(op.f("ix_reading_sessions_user_id"), "reading_sessions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reading_sessions_user_id"), table_name="reading_sessions")
    op.drop_index(op.f("ix_reading_sessions_owned_book_id"), table_name="reading_sessions")
    op.drop_table("reading_sessions")
