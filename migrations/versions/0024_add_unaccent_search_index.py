"""add unaccent-aware full-text search index on bibliographic_records

Revision ID: 0024_add_unaccent_search
Revises: 0023_add_active_loan_unique
Create Date: 2026-07-23

Root cause of "foreign titles are hard to find": to_tsvector('simple', ...) was
computed at query time with no index (full scan on every search) and did no
accent folding, so a query without diacritics never matched a title with them
(or vice versa) — exactly the case for transliterated foreign titles.

Postgres's unaccent() is marked STABLE, not IMMUTABLE, so it can't be used
directly in an index expression. immutable_unaccent() is a thin IMMUTABLE
wrapper around it (safe: unaccent's output only depends on its input and the
'unaccent' dictionary, which doesn't change at runtime) — the expression index
below requires it, and the repository query must call the same wrapper so the
two expressions match and Postgres can actually use the index.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0024_add_unaccent_search'
down_revision: Union[str, None] = '0023_add_active_loan_unique'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION immutable_unaccent(text)
        RETURNS text AS $$
            SELECT unaccent('unaccent', $1)
        $$ LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
        """
    )
    op.execute(
        """
        CREATE INDEX ix_bib_records_search_vector
        ON bibliographic_records
        USING GIN (
            to_tsvector(
                'simple',
                immutable_unaccent(
                    coalesce(title, '') || ' ' || coalesce(main_author, '') || ' ' || coalesce(isbn, '')
                )
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_bib_records_search_vector")
    op.execute("DROP FUNCTION IF EXISTS immutable_unaccent(text)")
