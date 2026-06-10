"""add owner_id to owned_books and create book_reads table

Revision ID: 0004_add_ownership_and_reads
Revises: 0003_add_current_reader
Create Date: 2026-06-10 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0004_add_ownership_and_reads"
down_revision = "0003_add_current_reader"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable, no FK: users live in the auth service's database.
    op.add_column("owned_books", sa.Column("owner_id", UUID(as_uuid=True), nullable=True))
    op.create_index("ix_owned_books_owner_id", "owned_books", ["owner_id"])

    op.create_table(
        "book_reads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        # FK within the same DB: cascade-delete when the owned_book is removed.
        sa.Column(
            "owned_book_id",
            UUID(as_uuid=True),
            sa.ForeignKey("owned_books.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # No FK: users live in the auth service's database.
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("owned_book_id", "user_id", name="uq_book_reads_book_user"),
    )
    op.create_index("ix_book_reads_owned_book_id", "book_reads", ["owned_book_id"])
    op.create_index("ix_book_reads_user_id", "book_reads", ["user_id"])


def downgrade() -> None:
    op.drop_table("book_reads")
    op.drop_index("ix_owned_books_owner_id", table_name="owned_books")
    op.drop_column("owned_books", "owner_id")
