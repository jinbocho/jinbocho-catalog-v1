from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class ReadingSessionMode(StrEnum):
    # Child reading alone — self-logged, logged_by_user_id stays None.
    INDEPENDENT = "independent"
    # KID-02: a parent reads aloud with a 0-5 child who has no autonomous
    # reading of their own yet. The parent logs it on the child's behalf.
    TOGETHER = "together"


@dataclass
class ReadingSession:
    owned_book_id: UUID
    # The child this session is for — users live in the auth service → bare
    # UUID, no FK (same convention as BookRead).
    user_id: UUID
    minutes: int | None = None
    pages: int | None = None
    session_date: date = field(default_factory=lambda: datetime.now(UTC).date())
    mode: ReadingSessionMode = ReadingSessionMode.INDEPENDENT
    # Who actually submitted this session — None for independent (self-logged)
    # sessions; set to the parent's id for "together" sessions.
    logged_by_user_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
