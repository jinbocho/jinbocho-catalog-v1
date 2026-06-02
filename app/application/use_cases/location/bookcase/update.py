from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import Bookcase
from app.domain.repositories import BookcaseRepository, RoomRepository
from app.utils import utcnow

from ..room.read import _get_room_for_family
from .read import _get_bookcase_for_family


@dataclass
class UpdateBookcaseInput:
	bookcase_id: UUID
	family_id: UUID
	room_id: UUID | None = None
	name: str | None = None
	description: str | None = None
	type: str | None = None
	notes: str | None = None
	image_url: str | None = None


class UpdateBookcaseUseCase:
	def __init__(self, bookcase_repo: BookcaseRepository, room_repo: RoomRepository) -> None:
		self._bookcase_repo = bookcase_repo
		self._room_repo = room_repo

	async def execute(self, inp: UpdateBookcaseInput) -> Bookcase:
		bookcase = await _get_bookcase_for_family(self._bookcase_repo, inp.bookcase_id, inp.family_id)
		if inp.room_id is not None:
			await _get_room_for_family(self._room_repo, inp.room_id, inp.family_id)
			bookcase.room_id = inp.room_id
		if inp.name is not None:
			bookcase.name = inp.name
		if inp.description is not None:
			bookcase.description = inp.description
		if inp.type is not None:
			bookcase.type = inp.type
		if inp.notes is not None:
			bookcase.notes = inp.notes
		if inp.image_url is not None:
			bookcase.image_url = inp.image_url
		bookcase.updated_at = utcnow()
		return await self._bookcase_repo.save(bookcase)
