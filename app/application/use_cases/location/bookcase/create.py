import logging
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import Bookcase
from app.domain.repositories import BookcaseRepository, RoomRepository
from app.utils import utcnow

from ..room.read import _get_room_for_family

logger = logging.getLogger(__name__)


@dataclass
class CreateBookcaseInput:
	family_id: UUID
	room_id: UUID
	name: str
	description: str | None = None
	type: str | None = None
	notes: str | None = None
	image_url: str | None = None


class CreateBookcaseUseCase:
	def __init__(self, bookcase_repo: BookcaseRepository, room_repo: RoomRepository) -> None:
		self._bookcase_repo = bookcase_repo
		self._room_repo = room_repo

	async def execute(self, inp: CreateBookcaseInput) -> Bookcase:
		await _get_room_for_family(self._room_repo, inp.room_id, inp.family_id)
		saved = await self._bookcase_repo.save(
			Bookcase(
				family_id=inp.family_id,
				room_id=inp.room_id,
				name=inp.name,
				description=inp.description,
				type=inp.type,
				notes=inp.notes,
				image_url=inp.image_url,
				created_at=utcnow(),
				updated_at=utcnow(),
			)
		)
		logger.info("Bookcase %s created in family %s", saved.id, inp.family_id)
		return saved
