from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class ParticipantStatus(StrEnum):
    JOINED = "joined"
    FINISHED = "finished"


@dataclass
class BookClubParticipant:
    cycle_id: UUID
    # Users live in the auth service → bare UUID, no FK. One row per user per
    # cycle (enforced by a unique constraint in the model).
    user_id: UUID
    status: ParticipantStatus = ParticipantStatus.JOINED
    id: UUID = field(default_factory=uuid4)
    joined_at: datetime = field(default_factory=lambda: datetime.now(UTC))
