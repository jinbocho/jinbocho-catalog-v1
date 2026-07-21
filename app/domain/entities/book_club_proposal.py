from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class BookClubProposal:
    library_id: UUID
    bibliographic_record_id: UUID
    # Users live in the auth service → bare UUID, no FK.
    proposed_by: UUID
    note: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
