from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import QuizQuestion


class QuizQuestionRepository(ABC):
    @abstractmethod
    async def add(self, question: QuizQuestion) -> QuizQuestion: ...

    @abstractmethod
    async def list_by_book(self, owned_book_id: UUID) -> list[QuizQuestion]: ...

    @abstractmethod
    async def find_by_ids(self, ids: list[UUID]) -> list[QuizQuestion]: ...
