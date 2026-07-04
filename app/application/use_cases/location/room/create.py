import logging
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import Room
from app.domain.repositories import RoomRepository
from app.utils import utcnow

logger = logging.getLogger(__name__)


@dataclass
class CreateRoomInput:
	family_id: UUID
	name: str
	description: str | None = None


class CreateRoomUseCase:
	def __init__(self, room_repo: RoomRepository) -> None:
		self._room_repo = room_repo

	async def execute(self, inp: CreateRoomInput) -> Room:
		saved = await self._room_repo.save(
			Room(
				family_id=inp.family_id,
				name=inp.name,
				description=inp.description,
				created_at=utcnow(),
				updated_at=utcnow(),
			)
		)
		logger.info("Room %s created in family %s", saved.id, inp.family_id)
		return saved
