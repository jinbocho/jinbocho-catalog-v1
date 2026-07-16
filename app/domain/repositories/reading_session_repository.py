from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import ReadingSession


class ReadingSessionRepository(ABC):
    @abstractmethod
    async def add(self, session: ReadingSession) -> ReadingSession: ...

    @abstractmethod
    async def list_by_user_and_library(self, user_id: UUID, library_id: UUID) -> list[ReadingSession]:
        """Scoped via a join to owned_books.library_id — reading_sessions has
        no library_id of its own (same rationale as BookRead), and this join
        is what stops a caller from listing another library's session data
        for a guessed user_id."""
        ...
