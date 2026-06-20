from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import BibliographicRecord


class BibliographicRecordRepository(ABC):
	@abstractmethod
	async def find_by_id(self, record_id: UUID) -> BibliographicRecord | None: ...

	@abstractmethod
	async def find_by_isbn(self, family_id: UUID, isbn: str) -> BibliographicRecord | None: ...

	@abstractmethod
	async def find_by_title_author(self, family_id: UUID, title: str, main_author: str | None) -> BibliographicRecord | None:
		"""Fallback dedupe key for library import when a record has no ISBN
		(find_by_isbn can't help there)."""
		...

	@abstractmethod
	async def find_all_by_family(
		self,
		family_id: UUID,
		q: str | None = None,
		genre: str | None = None,
		limit: int = 50,
		offset: int = 0,
	) -> list[BibliographicRecord]: ...

	@abstractmethod
	async def count_genres(self, family_id: UUID) -> list[tuple[str, int]]: ...

	@abstractmethod
	async def find_all_by_ids(self, record_ids: list[UUID]) -> list[BibliographicRecord]: ...

	@abstractmethod
	async def save(self, record: BibliographicRecord) -> BibliographicRecord: ...

	@abstractmethod
	async def delete(self, record_id: UUID) -> None: ...

	@abstractmethod
	async def delete_all_by_family(self, family_id: UUID) -> None:
		"""Bulk-deletes every record for the family — used by full account
		deletion. Caller must delete dependent owned_books first (RESTRICT)."""
		...
