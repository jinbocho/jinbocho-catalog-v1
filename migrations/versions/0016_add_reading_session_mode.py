"""add mode and logged_by_user_id to reading_sessions

Revision ID: 0016_add_reading_session_mode
Revises: 0015_add_discussion_questions
Create Date: 2026-07-17 00:00:00.000000

KID-02 shared reading 0-5: a parent can log a "together" session on behalf
of a child who has no autonomous reading yet, distinct from the existing
child self-service "independent" sessions. Additive, backfills existing
rows to 'independent' via server_default.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0016_add_reading_session_mode"
down_revision: Union[str, None] = "0015_add_discussion_questions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reading_sessions",
        sa.Column("mode", sa.String(length=11), nullable=False, server_default="independent"),
    )
    op.add_column("reading_sessions", sa.Column("logged_by_user_id", UUID(as_uuid=True), nullable=True))
    op.create_check_constraint(
        "ck_reading_sessions_mode", "reading_sessions", "mode IN ('independent','together')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_reading_sessions_mode", "reading_sessions", type_="check")
    op.drop_column("reading_sessions", "logged_by_user_id")
    op.drop_column("reading_sessions", "mode")
