import logging
from uuid import UUID

from app.domain.repositories import RoomRepository

from .read import _get_room_for_family

logger = logging.getLogger(__name__)


class DeleteRoomUseCase:
	def __init__(self, room_repo: RoomRepository) -> None:
		self._room_repo = room_repo

	async def execute(self, room_id: UUID, family_id: UUID) -> None:
		await _get_room_for_family(self._room_repo, room_id, family_id)
		await self._room_repo.delete(room_id)
		logger.info("Room %s deleted from family %s", room_id, family_id)
