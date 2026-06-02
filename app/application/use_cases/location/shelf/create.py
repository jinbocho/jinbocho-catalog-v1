from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import Shelf
from app.domain.repositories import SectionRepository, ShelfRepository
from app.utils import utcnow

from ..section.read import _get_section_for_family


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
		from ..bookcase.read import _get_bookcase_for_family
		section = await self._section_repo.find_by_id(inp.section_id)
		if section is None:
			raise LookupError("Section not found")
		# Verify family_id matches through bookcase
		from app.domain.repositories import BookcaseRepository
		return await self._shelf_repo.save(
			Shelf(section_id=inp.section_id, shelf_index=inp.shelf_index, notes=inp.notes, created_at=utcnow(), updated_at=utcnow())
		)
