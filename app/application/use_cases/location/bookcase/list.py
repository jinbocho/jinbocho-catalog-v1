from uuid import UUID

from app.domain.entities import Bookcase
from app.domain.repositories import BookcaseRepository, RoomRepository

from ..room.read import _get_room_for_library


class ListBookcasesUseCase:
	def __init__(self, bookcase_repo: BookcaseRepository, room_repo: RoomRepository) -> None:
		self._bookcase_repo = bookcase_repo
		self._room_repo = room_repo

	async def execute(
		self, library_id: UUID, room_id: UUID | None = None, limit: int = 50, offset: int = 0
	) -> list[Bookcase]:
		if room_id is not None:
			await _get_room_for_library(self._room_repo, room_id, library_id)
		return await self._bookcase_repo.find_all_by_library(library_id, room_id=room_id, limit=limit, offset=offset)
