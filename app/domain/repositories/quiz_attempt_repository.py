from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import QuizAttempt


class QuizAttemptRepository(ABC):
    @abstractmethod
    async def add(self, attempt: QuizAttempt) -> QuizAttempt: ...

    @abstractmethod
    async def find_by_id(self, attempt_id: UUID) -> QuizAttempt | None: ...

    @abstractmethod
    async def list_by_user_and_library(self, user_id: UUID, library_id: UUID) -> list[QuizAttempt]:
        """Scoped via a join to owned_books.library_id — same rationale as
        ReadingSessionRepository.list_by_user_and_library."""
        ...
