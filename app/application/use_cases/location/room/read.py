from uuid import UUID

from app.domain.entities import Room
from app.domain.repositories import RoomRepository


async def _get_room_for_library(room_repo: RoomRepository, room_id: UUID, library_id: UUID) -> Room:
	room = await room_repo.find_by_id(room_id)
	if room is None:
		raise LookupError("Room not found")
	if room.library_id != library_id:
		raise PermissionError("Access denied")
	return room


class GetRoomUseCase:
	def __init__(self, room_repo: RoomRepository) -> None:
		self._room_repo = room_repo

	async def execute(self, room_id: UUID, library_id: UUID) -> Room:
		return await _get_room_for_library(self._room_repo, room_id, library_id)
