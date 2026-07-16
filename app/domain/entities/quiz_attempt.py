from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class QuizAttempt:
    owned_book_id: UUID
    # Users (including child accounts) live in the auth service → bare UUID, no FK.
    user_id: UUID
    question_ids: list[UUID]
    answers: list[int]
    score: int
    total: int
    passed: bool
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
