"""add borrower_user_id to book_loans

Revision ID: 0011_add_book_loan_borrower_user
Revises: 0010_rename_family_to_library
Create Date: 2026-07-06 00:00:00.000000

Additive: nullable column, no default, no backfill needed — existing loans
stay exactly as they are (borrower_user_id = NULL, free-text borrower_name
only). Powers "lend to a Jinbocho user" search. No FK to auth-service's
users table: catalog_db and auth_db are separate databases (ADR-007), so
this is a weakly-typed UUID reference validated only at write time by the
use case, same pattern as owned_books.owner_id.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011_add_book_loan_borrower_user"
down_revision = "0010_rename_family_to_library"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("book_loans", sa.Column("borrower_user_id", postgresql.UUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    op.drop_column("book_loans", "borrower_user_id")
