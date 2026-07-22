import logging
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import Shelf
from app.domain.repositories import BookcaseRepository, SectionRepository, ShelfRepository
from app.utils import utcnow

from ..section.read import _get_section_for_library

logger = logging.getLogger(__name__)


@dataclass
class CreateShelfInput:
	library_id: UUID
	section_id: UUID
	shelf_index: int
	notes: str | None = None


class CreateShelfUseCase:
	def __init__(
		self, shelf_repo: ShelfRepository, section_repo: SectionRepository, bookcase_repo: BookcaseRepository
	) -> None:
		self._shelf_repo = shelf_repo
		self._section_repo = section_repo
		self._bookcase_repo = bookcase_repo

	async def execute(self, inp: CreateShelfInput) -> Shelf:
		await _get_section_for_library(self._section_repo, self._bookcase_repo, inp.section_id, inp.library_id)
		saved = await self._shelf_repo.save(
			Shelf(
				section_id=inp.section_id,
				shelf_index=inp.shelf_index,
				notes=inp.notes,
				created_at=utcnow(),
				updated_at=utcnow(),
			)
		)
		logger.info("Shelf %s created in library %s", saved.id, inp.library_id)
		return saved
