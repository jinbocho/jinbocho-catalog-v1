from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import BookHistory


class BookHistoryRepository(ABC):
	@abstractmethod
	async def find_by_book(self, book_id: UUID, limit: int = 50, offset: int = 0) -> list[BookHistory]: ...

	@abstractmethod
	async def save(self, history: BookHistory) -> BookHistory: ...
