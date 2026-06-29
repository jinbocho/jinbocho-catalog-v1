"""add book_ratings table

Revision ID: f953a4b39e75
Revises: 0009_add_wishlist_items
Create Date: 2026-06-29 12:25:14.028114

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f953a4b39e75"
down_revision: Union[str, None] = "0009_add_wishlist_items"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "book_ratings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owned_book_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("review", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_book_ratings_rating_range"),
        sa.ForeignKeyConstraint(["owned_book_id"], ["owned_books.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owned_book_id", "user_id", name="uq_book_ratings_book_user"),
    )
    op.create_index(op.f("ix_book_ratings_owned_book_id"), "book_ratings", ["owned_book_id"], unique=False)
    op.create_index(op.f("ix_book_ratings_user_id"), "book_ratings", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_book_ratings_user_id"), table_name="book_ratings")
    op.drop_index(op.f("ix_book_ratings_owned_book_id"), table_name="book_ratings")
    op.drop_table("book_ratings")
