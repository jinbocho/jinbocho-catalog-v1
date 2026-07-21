from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class ReadingPathSource(StrEnum):
    MANUAL = "manual"
    AI = "ai"


@dataclass
class ReadingPath:
    """KID-06 reading paths — a parent-curated (or, future, AI-suggested)
    ordered sequence of books from the family's own catalog, themed around
    something the child already likes. Completion is derived client-side
    from BookRead, same as the KID-10 portfolio — no progress stored here."""

    library_id: UUID
    title: str
    book_ids: list[UUID] = field(default_factory=list)
    description: str | None = None
    # One of "shared", "emerging", "fluent", "teen" (see KID-01), or None if
    # not age-targeted.
    target_band: str | None = None
    source: ReadingPathSource = ReadingPathSource.MANUAL
    created_by: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
