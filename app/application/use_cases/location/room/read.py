from uuid import UUID

from app.domain.entities import Room
from app.domain.repositories import RoomRepository


async def _get_room_for_family(room_repo: RoomRepository, room_id: UUID, family_id: UUID) -> Room:
	room = await room_repo.find_by_id(room_id)
	if room is None:
		raise LookupError("Room not found")
	if room.family_id != family_id:
		raise PermissionError("Access denied")
	return room


class GetRoomUseCase:
	def __init__(self, room_repo: RoomRepository) -> None:
		self._room_repo = room_repo

	async def execute(self, room_id: UUID, family_id: UUID) -> Room:
		return await _get_room_for_family(self._room_repo, room_id, family_id)
