"""add book club phase 2-3 tables (proposals, votes, participants, meetings, question sets)

Revision ID: 0022_add_book_club_phase2_3
Revises: 0021_add_book_club_tables
Create Date: 2026-07-21 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0022_add_book_club_phase2_3"
down_revision: Union[str, None] = "0021_add_book_club_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "book_club_proposals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("library_id", sa.UUID(), nullable=False),
        sa.Column("bibliographic_record_id", sa.UUID(), nullable=False),
        sa.Column("proposed_by", sa.UUID(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["bibliographic_record_id"], ["bibliographic_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_book_club_proposals_library_id"), "book_club_proposals", ["library_id"], unique=False)
    op.create_index(
        op.f("ix_book_club_proposals_bibliographic_record_id"),
        "book_club_proposals",
        ["bibliographic_record_id"],
        unique=False,
    )

    op.create_table(
        "book_club_votes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("proposal_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["proposal_id"], ["book_club_proposals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_id", "user_id", name="uq_book_club_votes_proposal_user"),
    )
    op.create_index(op.f("ix_book_club_votes_proposal_id"), "book_club_votes", ["proposal_id"], unique=False)
    op.create_index(op.f("ix_book_club_votes_user_id"), "book_club_votes", ["user_id"], unique=False)

    op.create_table(
        "book_club_participants",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("cycle_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="joined"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cycle_id"], ["book_club_cycles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cycle_id", "user_id", name="uq_book_club_participants_cycle_user"),
    )
    op.create_index(op.f("ix_book_club_participants_cycle_id"), "book_club_participants", ["cycle_id"], unique=False)
    op.create_index(op.f("ix_book_club_participants_user_id"), "book_club_participants", ["user_id"], unique=False)

    op.create_table(
        "book_club_meetings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("cycle_id", sa.UUID(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cycle_id"], ["book_club_cycles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_book_club_meetings_cycle_id"), "book_club_meetings", ["cycle_id"], unique=False)

    op.create_table(
        "book_club_question_sets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("cycle_id", sa.UUID(), nullable=False),
        sa.Column("language", sa.String(length=8), server_default="", nullable=False),
        sa.Column("questions", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cycle_id"], ["book_club_cycles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cycle_id", "language", name="uq_book_club_question_sets_cycle_language"),
    )
    op.create_index(
        op.f("ix_book_club_question_sets_cycle_id"), "book_club_question_sets", ["cycle_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_book_club_question_sets_cycle_id"), table_name="book_club_question_sets")
    op.drop_table("book_club_question_sets")
    op.drop_index(op.f("ix_book_club_meetings_cycle_id"), table_name="book_club_meetings")
    op.drop_table("book_club_meetings")
    op.drop_index(op.f("ix_book_club_participants_user_id"), table_name="book_club_participants")
    op.drop_index(op.f("ix_book_club_participants_cycle_id"), table_name="book_club_participants")
    op.drop_table("book_club_participants")
    op.drop_index(op.f("ix_book_club_votes_user_id"), table_name="book_club_votes")
    op.drop_index(op.f("ix_book_club_votes_proposal_id"), table_name="book_club_votes")
    op.drop_table("book_club_votes")
    op.drop_index(op.f("ix_book_club_proposals_bibliographic_record_id"), table_name="book_club_proposals")
    op.drop_index(op.f("ix_book_club_proposals_library_id"), table_name="book_club_proposals")
    op.drop_table("book_club_proposals")
