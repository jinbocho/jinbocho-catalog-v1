"""add current_reader_id to owned_books

Revision ID: 0003_add_current_reader
Revises: 0002_unique_family_isbn
Create Date: 2026-06-09 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "0003_add_current_reader"
down_revision = "0002_unique_family_isbn"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable, no FK: users live in the auth service's database.
    op.add_column("owned_books", sa.Column("current_reader_id", UUID(as_uuid=True), nullable=True))
    op.create_index("ix_owned_books_current_reader_id", "owned_books", ["current_reader_id"])


def downgrade() -> None:
    op.drop_index("ix_owned_books_current_reader_id", table_name="owned_books")
    op.drop_column("owned_books", "current_reader_id")
