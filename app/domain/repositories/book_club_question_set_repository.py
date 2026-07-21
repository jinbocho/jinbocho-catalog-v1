from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import BookClubQuestionSet


class BookClubQuestionSetRepository(ABC):
    @abstractmethod
    async def find_by_cycle_and_language(
        self, cycle_id: UUID, language: str
    ) -> BookClubQuestionSet | None: ...

    @abstractmethod
    async def save(self, question_set: BookClubQuestionSet) -> BookClubQuestionSet: ...
