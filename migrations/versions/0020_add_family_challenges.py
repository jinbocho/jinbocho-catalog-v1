"""create family_challenges table

Revision ID: 0020_add_family_challenges
Revises: 0019_add_mystery_picks
Create Date: 2026-07-17 00:00:00.000000

KID-08 cooperative family challenges: a single shared target the whole
library works toward together, no per-member leaderboard. See
jinbocho-docs/backlog/BACKLOG_KIDS_READING_EDUCATION.md.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020_add_family_challenges"
down_revision: Union[str, None] = "0019_add_mystery_picks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "family_challenges",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("library_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("metric", sa.String(length=10), nullable=False),
        sa.Column("target", sa.Integer(), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("metric IN ('minutes','sessions','books')", name="ck_family_challenges_metric"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_family_challenges_library_id"), "family_challenges", ["library_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_family_challenges_library_id"), table_name="family_challenges")
    op.drop_table("family_challenges")
