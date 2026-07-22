import logging
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import Shelf
from app.domain.repositories import BookcaseRepository, SectionRepository, ShelfRepository
from app.utils import utcnow

from ..section.read import _get_section_for_library
from .read import _get_shelf_for_library

logger = logging.getLogger(__name__)


@dataclass
class UpdateShelfInput:
	shelf_id: UUID
	library_id: UUID
	section_id: UUID | None = None
	shelf_index: int | None = None
	notes: str | None = None


class UpdateShelfUseCase:
	def __init__(
		self, shelf_repo: ShelfRepository, section_repo: SectionRepository, bookcase_repo: BookcaseRepository
	) -> None:
		self._shelf_repo = shelf_repo
		self._section_repo = section_repo
		self._bookcase_repo = bookcase_repo

	async def execute(self, inp: UpdateShelfInput) -> Shelf:
		shelf = await _get_shelf_for_library(
			self._shelf_repo, self._section_repo, self._bookcase_repo, inp.shelf_id, inp.library_id
		)
		if inp.section_id is not None:
			await _get_section_for_library(self._section_repo, self._bookcase_repo, inp.section_id, inp.library_id)
			shelf.section_id = inp.section_id
		if inp.shelf_index is not None:
			shelf.shelf_index = inp.shelf_index
		if inp.notes is not None:
			shelf.notes = inp.notes
		shelf.updated_at = utcnow()
		saved = await self._shelf_repo.save(shelf)
		logger.info("Shelf %s updated in library %s", saved.id, inp.library_id)
		return saved
