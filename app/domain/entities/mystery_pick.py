from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class MysteryPickStatus(StrEnum):
    # Parent proposed it; the child sees only the masked hint.
    PROPOSED = "proposed"
    # Child accepted the challenge — this is also the reveal moment: the
    # book's identity becomes visible to them from this point on.
    ACCEPTED = "accepted"


@dataclass
class MysteryPick:
    """KID-07 'libro al buio' — a parent picks a book from the family's own
    catalog and the child sees only an AI-masked hint (reused from the
    incipit feature) until they accept the challenge. See
    jinbocho-docs/backlog/BACKLOG_KIDS_READING_EDUCATION.md."""

    library_id: UUID
    owned_book_id: UUID
    child_user_id: UUID
    hint_text: str
    status: MysteryPickStatus = MysteryPickStatus.PROPOSED
    # Users live in the auth service → bare UUID, no FK.
    created_by: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
