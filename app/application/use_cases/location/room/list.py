from uuid import UUID

from app.domain.entities import Room
from app.domain.repositories import RoomRepository


class ListRoomsUseCase:
	def __init__(self, room_repo: RoomRepository) -> None:
		self._room_repo = room_repo

	async def execute(self, library_id: UUID, limit: int = 50, offset: int = 0) -> list[Room]:
		return await self._room_repo.find_all_by_library(library_id, limit=limit, offset=offset)
