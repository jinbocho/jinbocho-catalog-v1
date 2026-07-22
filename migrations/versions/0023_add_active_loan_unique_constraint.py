"""add partial unique constraint on book_loans to prevent concurrent double-loan

Revision ID: 0023_add_active_loan_unique
Revises: 0022_add_book_club_phase2_3
Create Date: 2026-07-22

Confirmed via pentest that LendBookUseCase's "already on loan" check
(get_active_for_book then add) is a plain read-then-write with no locking —
concurrent lend requests for the same book can all pass the check before any
of them commits. A partial unique index (Postgres-native, enforced regardless
of application-level races) is the correct fix, mirroring the existing
uq_wishlist_user_record constraint for the same class of invariant.

Before applying in production: verify no book currently has more than one
row with returned_at IS NULL (this migration does not clean up existing
violations, only prevents new ones).
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0023_add_active_loan_unique'
down_revision: Union[str, None] = '0022_add_book_club_phase2_3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'uq_book_loans_active_per_book',
        'book_loans',
        ['owned_book_id'],
        unique=True,
        postgresql_where='returned_at IS NULL',
    )


def downgrade() -> None:
    op.drop_index('uq_book_loans_active_per_book', table_name='book_loans')
