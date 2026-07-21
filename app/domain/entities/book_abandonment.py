from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class BookAbandonment:
    """A reader chose to stop reading this book — recorded as a neutral fact,
    never a failure (see KID-05 reader's rights in
    jinbocho-docs/backlog/BACKLOG_KIDS_READING_EDUCATION.md). Mirrors BookRead's
    shape: one row per (owned_book_id, user_id), mutually exclusive with it."""

    owned_book_id: UUID
    # Users live in the auth service → bare UUID, no FK.
    user_id: UUID
    abandoned_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    id: UUID = field(default_factory=uuid4)
