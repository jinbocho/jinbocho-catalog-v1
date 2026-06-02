from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import Room
from app.domain.repositories import RoomRepository
from app.utils import utcnow

from .read import _get_room_for_family


@dataclass
class UpdateRoomInput:
	room_id: UUID
	family_id: UUID
	name: str | None = None
	description: str | None = None


class UpdateRoomUseCase:
	def __init__(self, room_repo: RoomRepository) -> None:
		self._room_repo = room_repo

	async def execute(self, inp: UpdateRoomInput) -> Room:
		room = await _get_room_for_family(self._room_repo, inp.room_id, inp.family_id)
		if inp.name is not None:
			room.name = inp.name
		if inp.description is not None:
			room.description = inp.description
		room.updated_at = utcnow()
		return await self._room_repo.save(room)
