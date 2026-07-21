from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class BookClubMeeting:
    cycle_id: UUID
    scheduled_at: datetime
    # Users live in the auth service → bare UUID, no FK.
    created_by: UUID
    # Free text: a physical place or a video-call link.
    note: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
