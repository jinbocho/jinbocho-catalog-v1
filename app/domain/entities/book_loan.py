from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class BookLoan:
    owned_book_id: UUID
    borrower_name: str
    loaned_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    due_date: datetime | None = None
    returned_at: datetime | None = None
    reminder_sent_at: datetime | None = None
    id: UUID = field(default_factory=uuid4)
