"""rename family_id -> library_id (ADR-011 step 2)

Revision ID: 0010_rename_family_to_library
Revises: f953a4b39e75
Create Date: 2026-07-06 00:00:00.000000

Renames the tenant FK column from family_id to library_id across every table
that carries it. This service is already deployed, so this runs against a
populated production database — RENAME COLUMN and ALTER INDEX/CONSTRAINT
RENAME are metadata-only in Postgres (no table rewrite, no data movement),
safe without a maintenance window. Companion to auth-service's own
family->library rename migration (same ADR-011 step 2).
"""

from alembic import op

revision = "0010_rename_family_to_library"
down_revision = "f953a4b39e75"
branch_labels = None
depends_on = None

_TABLES = ("rooms", "bookcases", "bibliographic_records", "owned_books", "removed_members", "wishlist_items")


def upgrade() -> None:
    for table in _TABLES:
        op.alter_column(table, "family_id", new_column_name="library_id")
        op.execute(f"ALTER INDEX ix_{table}_family_id RENAME TO ix_{table}_library_id")
    op.execute("ALTER TABLE bibliographic_records RENAME CONSTRAINT uq_bib_family_isbn TO uq_bib_library_isbn")


def downgrade() -> None:
    op.execute("ALTER TABLE bibliographic_records RENAME CONSTRAINT uq_bib_library_isbn TO uq_bib_family_isbn")
    for table in _TABLES:
        op.execute(f"ALTER INDEX ix_{table}_library_id RENAME TO ix_{table}_family_id")
        op.alter_column(table, "library_id", new_column_name="family_id")
