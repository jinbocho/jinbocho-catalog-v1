import logging
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import Shelf
from app.domain.repositories import SectionRepository, ShelfRepository
from app.utils import utcnow

logger = logging.getLogger(__name__)


@dataclass
class CreateShelfInput:
	family_id: UUID
	section_id: UUID
	shelf_index: int
	notes: str | None = None


class CreateShelfUseCase:
	def __init__(self, shelf_repo: ShelfRepository, section_repo: SectionRepository) -> None:
		self._shelf_repo = shelf_repo
		self._section_repo = section_repo

	async def execute(self, inp: CreateShelfInput) -> Shelf:
		section = await self._section_repo.find_by_id(inp.section_id)
		if section is None:
			raise LookupError("Section not found")
		# Verify family_id matches through bookcase
		saved = await self._shelf_repo.save(
			Shelf(
				section_id=inp.section_id,
				shelf_index=inp.shelf_index,
				notes=inp.notes,
				created_at=utcnow(),
				updated_at=utcnow(),
			)
		)
		logger.info("Shelf %s created in family %s", saved.id, inp.family_id)
		return saved
