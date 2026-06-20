from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import Section


class SectionRepository(ABC):
	@abstractmethod
	async def find_by_id(self, section_id: UUID) -> Section | None: ...

	@abstractmethod
	async def find_all_by_bookcase(self, bookcase_id: UUID, limit: int = 50, offset: int = 0) -> list[Section]: ...

	@abstractmethod
	async def find_all_by_family(
		self,
		family_id: UUID,
		bookcase_id: UUID | None = None,
		limit: int = 50,
		offset: int = 0,
	) -> list[Section]: ...

	@abstractmethod
	async def find_by_index(self, bookcase_id: UUID, section_index: int) -> Section | None:
		"""Lookup by the (bookcase_id, section_index) the DB already enforces as
		unique — used to dedupe on library import."""
		...

	@abstractmethod
	async def save(self, section: Section) -> Section: ...

	@abstractmethod
	async def delete(self, section_id: UUID) -> None: ...
