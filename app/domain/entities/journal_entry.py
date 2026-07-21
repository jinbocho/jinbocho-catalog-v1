from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class JournalPromptKind(StrEnum):
    # Free response — any age, any length.
    FREE = "free"
    # 9-12: "tell me what happened" — retelling is a more valid comprehension
    # signal than multiple choice (see KID-03 in
    # jinbocho-docs/backlog/BACKLOG_KIDS_READING_EDUCATION.md).
    RETELLING = "retelling"
    # Rodari-inspired creative prompts ("invent a different ending").
    CREATIVE = "creative"


@dataclass
class JournalEntry:
    owned_book_id: UUID
    # Users live in the auth service → bare UUID, no FK (same convention as BookRead).
    user_id: UUID
    text: str
    prompt_kind: JournalPromptKind = JournalPromptKind.FREE
    # 6-8: emoji + one sentence instead of a full retelling.
    emoji: str | None = None
    # Links to the reading session this entry was written after, if any —
    # same-DB FK, unlike user_id/owned_book_id which cross services.
    session_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
