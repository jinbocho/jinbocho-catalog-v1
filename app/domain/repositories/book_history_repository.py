from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import BookHistory


class BookHistoryRepository(ABC):
	@abstractmethod
	async def find_by_book(self, book_id: UUID, limit: int = 50, offset: int = 0) -> list[BookHistory]: ...

	@abstractmethod
	async def save(self, history: BookHistory) -> BookHistory: ...

	@abstractmethod
	async def find_all_by_family(self, family_id: UUID) -> list[BookHistory]:
		"""All history for the family's currently-existing books, for a full
		library export. There's no FK on owned_book_id (audit rows survive book
		deletion), so this can only join against books that still exist — history
		for an already-deleted book is not attributable to a family this way."""
		...

	@abstractmethod
	async def restore(self, history: BookHistory) -> BookHistory:
		"""Upsert by id — for library import, unlike save() which always does a
		blind insert (fine for its normal callers, which only ever use fresh
		ids, but would collide on a primary key re-importing the same backup)."""
		...
