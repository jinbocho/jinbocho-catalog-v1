"""add book_loans table

Revision ID: 0005_add_book_loans
Revises: 0004_add_ownership_and_reads
Create Date: 2026-06-10 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0005_add_book_loans"
down_revision = "0004_add_ownership_and_reads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "book_loans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "owned_book_id",
            UUID(as_uuid=True),
            sa.ForeignKey("owned_books.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("borrower_name", sa.String(255), nullable=False),
        sa.Column("loaned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_book_loans_owned_book_id", "book_loans", ["owned_book_id"])
    op.create_index("ix_book_loans_returned_at", "book_loans", ["returned_at"])


def downgrade() -> None:
    op.drop_table("book_loans")
