from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class ChallengeMetric(StrEnum):
    MINUTES = "minutes"
    SESSIONS = "sessions"
    BOOKS = "books"


@dataclass
class FamilyChallenge:
    """KID-08 cooperative family challenge — a single shared target the
    whole library works toward together. Deliberately no per-member
    breakdown surfaced anywhere: the point is one shared bar, never a
    leaderboard between siblings. See
    jinbocho-docs/backlog/BACKLOG_KIDS_READING_EDUCATION.md."""

    library_id: UUID
    title: str
    metric: ChallengeMetric
    target: int
    starts_on: date
    ends_on: date
    created_by: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
