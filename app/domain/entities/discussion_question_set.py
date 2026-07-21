from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class DiscussionQuestionSet:
    """KID-04 'dinner-table questions' — cached AI-generated conversation
    starters for a parent, one set per book (get-or-generate, like quiz
    questions, so the LLM isn't repaid on every dashboard view). See
    jinbocho-docs/backlog/BACKLOG_KIDS_READING_EDUCATION.md."""

    owned_book_id: UUID
    questions: list[str] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
