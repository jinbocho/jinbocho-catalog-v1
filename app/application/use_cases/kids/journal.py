import logging
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import JournalEntry, JournalPromptKind
from app.domain.repositories import JournalEntryRepository, OwnedBookRepository

logger = logging.getLogger(__name__)


@dataclass
class CreateJournalEntryInput:
    owned_book_id: UUID
    library_id: UUID
    user_id: UUID
    kids_mode_enabled: bool
    text: str
    prompt_kind: JournalPromptKind = JournalPromptKind.FREE
    emoji: str | None = None
    session_id: UUID | None = None


class CreateJournalEntryUseCase:
    """Child self-service: the caller always writes their own entry — same
    coordination model as LogReadingSessionUseCase (no "log on behalf of"
    path here; KID-02's parent-authored exception is specific to shared
    reading sessions, not journal entries)."""

    def __init__(self, book_repo: OwnedBookRepository, entry_repo: JournalEntryRepository) -> None:
        self._book_repo = book_repo
        self._entry_repo = entry_repo

    async def execute(self, input: CreateJournalEntryInput) -> JournalEntry:
        if not input.kids_mode_enabled:
            raise PermissionError("Kids mode is not enabled for this library")
        book = await self._book_repo.find_by_id(input.owned_book_id)
        if not book:
            raise LookupError("Book not found")
        if book.library_id != input.library_id:
            raise PermissionError("Book does not belong to this library")

        entry = JournalEntry(
            owned_book_id=input.owned_book_id,
            user_id=input.user_id,
            text=input.text,
            prompt_kind=input.prompt_kind,
            emoji=input.emoji,
            session_id=input.session_id,
        )
        saved = await self._entry_repo.add(entry)
        logger.info("Journal entry written by user %s for book %s", input.user_id, input.owned_book_id)
        return saved


@dataclass
class ListJournalEntriesInput:
    target_user_id: UUID
    library_id: UUID
    requester_user_id: UUID
    requester_role: str
    kids_mode_enabled: bool


class ListJournalEntriesUseCase:
    """A child sees only their own entries; a parent (admin/editor) can view
    any member's, read-only, for the parent dashboard feed."""

    def __init__(self, entry_repo: JournalEntryRepository) -> None:
        self._entry_repo = entry_repo

    async def execute(self, input: ListJournalEntriesInput) -> list[JournalEntry]:
        if not input.kids_mode_enabled:
            raise PermissionError("Kids mode is not enabled for this library")
        is_self = input.target_user_id == input.requester_user_id
        is_parent = input.requester_role in ("admin", "editor")
        if not is_self and not is_parent:
            raise PermissionError("Cannot view another user's journal entries")
        return await self._entry_repo.list_by_user_and_library(input.target_user_id, input.library_id)
