from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import BookEventType, BookHistory


class BookHistoryRepository(ABC):
	@abstractmethod
	async def find_by_book(self, book_id: UUID, limit: int = 50, offset: int = 0) -> list[BookHistory]: ...

	@abstractmethod
	async def save(self, history: BookHistory) -> BookHistory: ...

	@abstractmethod
	async def find_all_by_library(self, library_id: UUID) -> list[BookHistory]:
		"""All history for the library's currently-existing books, for a full
		library export. There's no FK on owned_book_id (audit rows survive book
		deletion), so this can only join against books that still exist — history
		for an already-deleted book is not attributable to a library this way."""
		...

	@abstractmethod
	async def find_recent_by_library(
		self, library_id: UUID, event_types: list[BookEventType], limit: int = 20
	) -> list[BookHistory]:
		"""Most recent history rows for the library's activity feed, filtered to
		`event_types` (the feed deliberately omits noisy/sensitive events like
		metadata_updated and deleted — see dashboard planning discussion) and
		bounded by `limit` at the DB level, unlike find_all_by_library which is
		unbounded and only meant for full export."""
		...

	@abstractmethod
	async def restore(self, history: BookHistory) -> BookHistory:
		"""Upsert by id — for library import, unlike save() which always does a
		blind insert (fine for its normal callers, which only ever use fresh
		ids, but would collide on a primary key re-importing the same backup)."""
		...

	@abstractmethod
	async def delete_by_owned_book_ids(self, owned_book_ids: list[UUID]) -> None:
		"""Used by full account deletion — there's no FK/library_id on this
		table, so the caller resolves the library's book ids first (e.g. via
		OwnedBookRepository.find_all_by_library) and must do so before deleting
		those books."""
		...
