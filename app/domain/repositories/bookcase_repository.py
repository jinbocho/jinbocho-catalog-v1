from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import Bookcase


class BookcaseRepository(ABC):
	@abstractmethod
	async def find_by_id(self, bookcase_id: UUID) -> Bookcase | None: ...

	@abstractmethod
	async def find_all_by_family(
		self,
		family_id: UUID,
		room_id: UUID | None = None,
		limit: int = 50,
		offset: int = 0,
	) -> list[Bookcase]: ...

	@abstractmethod
	async def find_by_name(self, room_id: UUID, name: str) -> Bookcase | None:
		"""Exact-name lookup within the room — used to dedupe on library import."""
		...

	@abstractmethod
	async def save(self, bookcase: Bookcase) -> Bookcase: ...

	@abstractmethod
	async def delete(self, bookcase_id: UUID) -> None: ...
