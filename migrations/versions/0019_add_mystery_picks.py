"""create mystery_picks table

Revision ID: 0019_add_mystery_picks
Revises: 0018_add_reading_paths
Create Date: 2026-07-17 00:00:00.000000

KID-07 "libro al buio": a parent picks a book from the catalog and the
child sees only a masked hint (reused from the incipit feature) until they
accept the challenge. See
jinbocho-docs/backlog/BACKLOG_KIDS_READING_EDUCATION.md.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0019_add_mystery_picks"
down_revision: Union[str, None] = "0018_add_reading_paths"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mystery_picks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("library_id", sa.UUID(), nullable=False),
        sa.Column("owned_book_id", sa.UUID(), nullable=False),
        sa.Column("child_user_id", sa.UUID(), nullable=False),
        sa.Column("hint_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="proposed"),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('proposed','accepted')", name="ck_mystery_picks_status"),
        sa.ForeignKeyConstraint(["owned_book_id"], ["owned_books.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mystery_picks_library_id"), "mystery_picks", ["library_id"], unique=False)
    op.create_index(op.f("ix_mystery_picks_owned_book_id"), "mystery_picks", ["owned_book_id"], unique=False)
    op.create_index(op.f("ix_mystery_picks_child_user_id"), "mystery_picks", ["child_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_mystery_picks_child_user_id"), table_name="mystery_picks")
    op.drop_index(op.f("ix_mystery_picks_owned_book_id"), table_name="mystery_picks")
    op.drop_index(op.f("ix_mystery_picks_library_id"), table_name="mystery_picks")
    op.drop_table("mystery_picks")
