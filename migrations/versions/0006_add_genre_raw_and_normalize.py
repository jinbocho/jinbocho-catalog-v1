"""add genre_raw column and normalize existing genres

Revision ID: 0006_add_genre_raw_and_normalize
Revises: 0005_add_book_loans
Create Date: 2026-06-11 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

from app.domain.entities.genre import map_to_genre

revision = "0006_add_genre_raw_and_normalize"
down_revision = "0005_add_book_loans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bibliographic_records", sa.Column("genre_raw", sa.String(255), nullable=True))
    op.create_index("ix_bibliographic_records_genre", "bibliographic_records", ["genre"])

    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, genre FROM bibliographic_records WHERE genre IS NOT NULL")
    ).fetchall()
    for row_id, raw_genre in rows:
        normalized = map_to_genre(raw_genre)
        bind.execute(
            sa.text("UPDATE bibliographic_records SET genre_raw = :raw, genre = :code WHERE id = :id"),
            {"raw": raw_genre, "code": normalized.value if normalized else None, "id": row_id},
        )


def downgrade() -> None:
    # Best-effort restore of the original free-text genre before dropping genre_raw.
    bind = op.get_bind()
    bind.execute(
        sa.text("UPDATE bibliographic_records SET genre = genre_raw WHERE genre_raw IS NOT NULL")
    )
    op.drop_index("ix_bibliographic_records_genre", table_name="bibliographic_records")
    op.drop_column("bibliographic_records", "genre_raw")
