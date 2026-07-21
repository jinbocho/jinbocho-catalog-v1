from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import DiscussionQuestionSet


class DiscussionQuestionSetRepository(ABC):
	@abstractmethod
	async def find_by_book(self, owned_book_id: UUID) -> DiscussionQuestionSet | None: ...

	@abstractmethod
	async def save(self, question_set: DiscussionQuestionSet) -> DiscussionQuestionSet: ...
