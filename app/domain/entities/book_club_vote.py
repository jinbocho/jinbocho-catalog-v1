from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class BookClubVote:
    proposal_id: UUID
    # Users live in the auth service → bare UUID, no FK. One vote per user per
    # proposal (enforced by a unique constraint in the model).
    user_id: UUID
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
