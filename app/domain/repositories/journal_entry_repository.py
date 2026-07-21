from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import JournalEntry


class JournalEntryRepository(ABC):
    @abstractmethod
    async def add(self, entry: JournalEntry) -> JournalEntry: ...

    @abstractmethod
    async def list_by_user_and_library(self, user_id: UUID, library_id: UUID) -> list[JournalEntry]:
        """Scoped via a join to owned_books.library_id — journal_entries has
        no library_id of its own (same rationale as ReadingSession)."""
        ...
