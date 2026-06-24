"""add reminder_sent_at to book_loans

Revision ID: 4fb4fc3f9b68
Revises: 0008_add_removed_members
Create Date: 2026-06-23 15:20:43.389517

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4fb4fc3f9b68'
down_revision: Union[str, None] = '0008_add_removed_members'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Note: autogenerate also flagged unrelated pre-existing drift (NOT NULL
    # on several created_at/updated_at columns, a couple of missing indexes)
    # — left untouched here, out of scope for this change.
    op.add_column('book_loans', sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('book_loans', 'reminder_sent_at')
