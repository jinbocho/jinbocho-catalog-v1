"""add quiz_questions and quiz_attempts tables

Revision ID: 0013_add_quiz_tables
Revises: 0012_add_reading_sessions
Create Date: 2026-07-16 00:00:00.000000

Kids Mode comprehension quiz: questions are either AI-generated (from book
metadata/incipit) or manually authored by a parent; attempts are scored and
retakes are allowed (no uniqueness constraint, unlike book_ratings). No FK on
user_id / author_user_id — catalog_db and auth_db are separate databases
(ADR-007), same pattern as reading_sessions.user_id.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_add_quiz_tables"
down_revision: Union[str, None] = "0012_add_reading_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quiz_questions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owned_book_id", sa.UUID(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("choices", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("correct_index", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=10), nullable=False),
        sa.Column("author_user_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("source IN ('ai','manual')", name="ck_quiz_questions_source"),
        sa.ForeignKeyConstraint(["owned_book_id"], ["owned_books.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quiz_questions_owned_book_id"), "quiz_questions", ["owned_book_id"], unique=False)

    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owned_book_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("question_ids", postgresql.ARRAY(sa.UUID()), nullable=False),
        sa.Column("answers", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("score >= 0 AND score <= total", name="ck_quiz_attempts_score_range"),
        sa.ForeignKeyConstraint(["owned_book_id"], ["owned_books.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quiz_attempts_owned_book_id"), "quiz_attempts", ["owned_book_id"], unique=False)
    op.create_index(op.f("ix_quiz_attempts_user_id"), "quiz_attempts", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_quiz_attempts_user_id"), table_name="quiz_attempts")
    op.drop_index(op.f("ix_quiz_attempts_owned_book_id"), table_name="quiz_attempts")
    op.drop_table("quiz_attempts")
    op.drop_index(op.f("ix_quiz_questions_owned_book_id"), table_name="quiz_questions")
    op.drop_table("quiz_questions")
