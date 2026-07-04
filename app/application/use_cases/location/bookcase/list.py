from uuid import UUID

from app.domain.entities import Bookcase
from app.domain.repositories import BookcaseRepository, RoomRepository

from ..room.read import _get_room_for_family


class ListBookcasesUseCase:
	def __init__(self, bookcase_repo: BookcaseRepository, room_repo: RoomRepository) -> None:
		self._bookcase_repo = bookcase_repo
		self._room_repo = room_repo

	async def execute(
		self, family_id: UUID, room_id: UUID | None = None, limit: int = 50, offset: int = 0
	) -> list[Bookcase]:
		if room_id is not None:
			await _get_room_for_family(self._room_repo, room_id, family_id)
		return await self._bookcase_repo.find_all_by_family(family_id, room_id=room_id, limit=limit, offset=offset)
