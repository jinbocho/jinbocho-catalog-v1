from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class BookClubPost:
    cycle_id: UUID
    # Users live in the auth service → bare UUID, no FK.
    user_id: UUID
    body: str
    # Reply threading within the same cycle; None for a top-level post.
    parent_post_id: UUID | None = None
    is_spoiler: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.body.strip():
            raise ValueError("post body must not be empty")
