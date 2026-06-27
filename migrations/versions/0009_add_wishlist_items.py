"""add wishlist_items table

Revision ID: 0009_add_wishlist_items
Revises: 4fb4fc3f9b68
Create Date: 2026-06-26 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0009_add_wishlist_items"
down_revision: Union[str, None] = "4fb4fc3f9b68"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wishlist_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("family_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "bibliographic_record_id",
            UUID(as_uuid=True),
            sa.ForeignKey("bibliographic_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("priority", sa.Integer, nullable=True),
    )
    op.create_index("ix_wishlist_items_family_id", "wishlist_items", ["family_id"])
    op.create_index("ix_wishlist_items_user_id", "wishlist_items", ["user_id"])
    op.create_unique_constraint(
        "uq_wishlist_user_record",
        "wishlist_items",
        ["user_id", "bibliographic_record_id"],
    )


def downgrade() -> None:
    op.drop_table("wishlist_items")
