"""add book club tables

Revision ID: 0021_add_book_club_tables
Revises: 0020_add_family_challenges
Create Date: 2026-07-20 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0021_add_book_club_tables"
down_revision: Union[str, None] = "0020_add_family_challenges"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "book_club_cycles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("library_id", sa.UUID(), nullable=False),
        sa.Column("bibliographic_record_id", sa.UUID(), nullable=False),
        sa.Column("owned_book_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="reading"),
        sa.Column("reading_start", sa.Date(), nullable=True),
        sa.Column("reading_end", sa.Date(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["bibliographic_record_id"], ["bibliographic_records.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["owned_book_id"], ["owned_books.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_book_club_cycles_library_id"), "book_club_cycles", ["library_id"], unique=False)
    op.create_index(
        op.f("ix_book_club_cycles_bibliographic_record_id"),
        "book_club_cycles",
        ["bibliographic_record_id"],
        unique=False,
    )

    op.create_table(
        "book_club_posts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("cycle_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("parent_post_id", sa.UUID(), nullable=True),
        sa.Column("is_spoiler", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cycle_id"], ["book_club_cycles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_post_id"], ["book_club_posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_book_club_posts_cycle_id"), "book_club_posts", ["cycle_id"], unique=False)
    op.create_index(op.f("ix_book_club_posts_user_id"), "book_club_posts", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_book_club_posts_user_id"), table_name="book_club_posts")
    op.drop_index(op.f("ix_book_club_posts_cycle_id"), table_name="book_club_posts")
    op.drop_table("book_club_posts")
    op.drop_index(op.f("ix_book_club_cycles_bibliographic_record_id"), table_name="book_club_cycles")
    op.drop_index(op.f("ix_book_club_cycles_library_id"), table_name="book_club_cycles")
    op.drop_table("book_club_cycles")
