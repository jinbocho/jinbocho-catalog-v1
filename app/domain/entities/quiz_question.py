from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class QuizSource(StrEnum):
    AI = "ai"
    MANUAL = "manual"


@dataclass
class QuizQuestion:
    owned_book_id: UUID
    prompt: str
    choices: list[str]
    correct_index: int
    source: QuizSource
    # None for AI-generated questions; set to the authoring parent's user_id for manual ones.
    author_user_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
