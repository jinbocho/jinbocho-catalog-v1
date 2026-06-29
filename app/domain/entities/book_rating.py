from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class BookRating:
    owned_book_id: UUID
    # Users live in the auth service → bare UUID, no FK.
    user_id: UUID
    rating: int
    review: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not 1 <= self.rating <= 5:
            raise ValueError("rating must be between 1 and 5")
