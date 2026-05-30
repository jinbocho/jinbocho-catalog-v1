"""add unique family isbn constraint

Revision ID: 0002_unique_family_isbn
Revises: 0001_initial_schema
Create Date: 2026-05-30 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_unique_family_isbn"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_bib_family_isbn", "bibliographic_records", ["family_id", "isbn"])


def downgrade() -> None:
    op.drop_constraint("uq_bib_family_isbn", "bibliographic_records", type_="unique")
