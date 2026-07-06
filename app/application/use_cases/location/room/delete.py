import logging
from uuid import UUID

from app.domain.repositories import RoomRepository

from .read import _get_room_for_library

logger = logging.getLogger(__name__)


class DeleteRoomUseCase:
	def __init__(self, room_repo: RoomRepository) -> None:
		self._room_repo = room_repo

	async def execute(self, room_id: UUID, library_id: UUID) -> None:
		await _get_room_for_library(self._room_repo, room_id, library_id)
		await self._room_repo.delete(room_id)
		logger.info("Room %s deleted from library %s", room_id, library_id)
