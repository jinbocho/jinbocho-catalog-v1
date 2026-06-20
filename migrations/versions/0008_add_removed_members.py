"""add removed_members table

Revision ID: 0008_add_removed_members
Revises: 0007_add_incipit
Create Date: 2026-06-20 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0008_add_removed_members"
down_revision = "0007_add_incipit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "removed_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("family_id", UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("removed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_removed_members_family_id", "removed_members", ["family_id"])


def downgrade() -> None:
    op.drop_table("removed_members")
