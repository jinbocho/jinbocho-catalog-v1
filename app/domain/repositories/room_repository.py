from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import Room


class RoomRepository(ABC):
	@abstractmethod
	async def find_by_id(self, room_id: UUID) -> Room | None: ...

	@abstractmethod
	async def find_all_by_family(self, family_id: UUID, limit: int = 50, offset: int = 0) -> list[Room]: ...

	@abstractmethod
	async def find_by_name(self, family_id: UUID, name: str) -> Room | None:
		"""Exact-name lookup within the family — used to dedupe on library import."""
		...

	@abstractmethod
	async def save(self, room: Room) -> Room: ...

	@abstractmethod
	async def delete(self, room_id: UUID) -> None: ...
