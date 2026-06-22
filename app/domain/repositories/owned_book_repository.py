from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import OwnedBook, ReadingStatus


class OwnedBookRepository(ABC):
	@abstractmethod
	async def find_by_id(self, book_id: UUID) -> OwnedBook | None: ...

	@abstractmethod
	async def find_all_by_family(
		self,
		family_id: UUID,
		shelf_id: UUID | None = None,
		reading_status: ReadingStatus | None = None,
		tag: str | None = None,
		limit: int = 50,
		offset: int = 0,
	) -> list[OwnedBook]: ...

	@abstractmethod
	async def find_all_by_shelf_ids(self, shelf_ids: list[UUID]) -> list[OwnedBook]: ...

	@abstractmethod
	async def exists_by_bibliographic_record_id(self, record_id: UUID) -> bool: ...

	@abstractmethod
	async def find_duplicate(
		self,
		family_id: UUID,
		bibliographic_record_id: UUID,
		room_id: UUID | None,
		bookcase_id: UUID | None,
		section_id: UUID | None,
		shelf_id: UUID | None,
		shelf_position: int | None,
	) -> OwnedBook | None:
		"""Same record in the exact same physical slot — used to dedupe on
		library import. A book with the same record but a different (or no)
		location is treated as a genuinely separate copy, not a duplicate."""
		...

	@abstractmethod
	async def find_one_by_record(self, bibliographic_record_id: UUID) -> OwnedBook | None:
		"""Any existing copy of this record, regardless of owner or location —
		used to warn about a likely duplicate when adding a new book. Family-
		wide on purpose: two members can legitimately each own a copy, so the
		check doesn't block that, it just surfaces who already has it (the
		caller decides whether to add a separate copy anyway)."""
		...

	@abstractmethod
	async def save(self, owned_book: OwnedBook) -> OwnedBook: ...

	@abstractmethod
	async def delete(self, book_id: UUID) -> None: ...

	@abstractmethod
	async def delete_all_by_family(self, family_id: UUID) -> None:
		"""Bulk-deletes every owned book for the family (reads/loans cascade at
		the DB level) — used by full account deletion. Caller must do this
		before deleting bibliographic records (RESTRICT)."""
		...
