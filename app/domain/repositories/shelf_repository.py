from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import Shelf


class ShelfRepository(ABC):
	@abstractmethod
	async def find_by_id(self, shelf_id: UUID) -> Shelf | None: ...

	@abstractmethod
	async def find_all_by_section(self, section_id: UUID, limit: int = 50, offset: int = 0) -> list[Shelf]: ...

	@abstractmethod
	async def find_all_by_family(
		self,
		family_id: UUID,
		section_id: UUID | None = None,
		limit: int = 50,
		offset: int = 0,
	) -> list[Shelf]: ...

	@abstractmethod
	async def find_by_index(self, section_id: UUID, shelf_index: int) -> Shelf | None:
		"""Lookup by the (section_id, shelf_index) the DB already enforces as
		unique — used to dedupe on library import."""
		...

	@abstractmethod
	async def save(self, shelf: Shelf) -> Shelf: ...

	@abstractmethod
	async def delete(self, shelf_id: UUID) -> None: ...
