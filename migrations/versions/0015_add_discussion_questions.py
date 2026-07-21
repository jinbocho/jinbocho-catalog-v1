"""create discussion_question_sets table

Revision ID: 0015_add_discussion_questions
Revises: 0014_add_book_abandonments
Create Date: 2026-07-17 00:00:00.000000

KID-04 "dinner-table questions": AI-generated conversation starters for a
parent, cached one set per book so the LLM isn't repaid on every dashboard
view. See jinbocho-docs/backlog/BACKLOG_KIDS_READING_EDUCATION.md.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_add_discussion_questions"
down_revision: Union[str, None] = "0014_add_book_abandonments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "discussion_question_sets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owned_book_id", sa.UUID(), nullable=False),
        sa.Column("questions", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owned_book_id"], ["owned_books.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_discussion_question_sets_owned_book_id"),
        "discussion_question_sets",
        ["owned_book_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_discussion_question_sets_owned_book_id"), table_name="discussion_question_sets")
    op.drop_table("discussion_question_sets")
