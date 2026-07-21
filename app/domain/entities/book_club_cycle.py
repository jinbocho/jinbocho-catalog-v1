from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class BookClubCycleStatus(StrEnum):
    # proposing/voting are reserved for the phase-2 proposal flow (CLUB-06);
    # in the MVP a cycle is created straight into READING.
    PROPOSING = "proposing"
    VOTING = "voting"
    READING = "reading"
    DISCUSSING = "discussing"
    ARCHIVED = "archived"


# Forward moves plus a one-step undo for each: DISCUSSING -> READING undoes
# "move to discussion" (a manager's mis-click shouldn't lock discussion in or
# out irreversibly), and ARCHIVED -> DISCUSSING reopens a cycle closed by
# mistake. Archiving itself only leaves DISCUSSING — a cycle must have gone
# through discussion before it can be closed.
_ALLOWED_TRANSITIONS: dict[BookClubCycleStatus, set[BookClubCycleStatus]] = {
    BookClubCycleStatus.PROPOSING: {BookClubCycleStatus.VOTING, BookClubCycleStatus.READING},
    BookClubCycleStatus.VOTING: {BookClubCycleStatus.READING},
    BookClubCycleStatus.READING: {BookClubCycleStatus.DISCUSSING},
    BookClubCycleStatus.DISCUSSING: {BookClubCycleStatus.ARCHIVED, BookClubCycleStatus.READING},
    BookClubCycleStatus.ARCHIVED: {BookClubCycleStatus.DISCUSSING},
}


@dataclass
class BookClubCycle:
    library_id: UUID
    bibliographic_record_id: UUID
    title: str
    created_by: UUID
    # The physical copy the club reads, when the library owns one. None when
    # the club reads a record nobody has shelved yet.
    owned_book_id: UUID | None = None
    status: BookClubCycleStatus = BookClubCycleStatus.READING
    reading_start: date | None = None
    reading_end: date | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("title must not be empty")

    def can_transition_to(self, target: BookClubCycleStatus) -> bool:
        return target in _ALLOWED_TRANSITIONS[self.status]
