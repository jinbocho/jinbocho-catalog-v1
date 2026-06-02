from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import BibliographicRecord


class BibliographicRecordRepository(ABC):
	@abstractmethod
	async def find_by_id(self, record_id: UUID) -> BibliographicRecord | None: ...

	@abstractmethod
	async def find_by_isbn(self, family_id: UUID, isbn: str) -> BibliographicRecord | None: ...

	@abstractmethod
	async def find_all_by_family(
		self,
		family_id: UUID,
		q: str | None = None,
		limit: int = 50,
		offset: int = 0,
	) -> list[BibliographicRecord]: ...

	@abstractmethod
	async def find_all_by_ids(self, record_ids: list[UUID]) -> list[BibliographicRecord]: ...

	@abstractmethod
	async def save(self, record: BibliographicRecord) -> BibliographicRecord: ...

	@abstractmethod
	async def delete(self, record_id: UUID) -> None: ...
