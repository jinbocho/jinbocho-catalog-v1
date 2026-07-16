from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from uuid import UUID, uuid4


@dataclass
class ReadingSession:
    owned_book_id: UUID
    # Users live in the auth service → bare UUID, no FK (same convention as BookRead).
    user_id: UUID
    minutes: int | None = None
    pages: int | None = None
    session_date: date = field(default_factory=lambda: datetime.now(UTC).date())
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
