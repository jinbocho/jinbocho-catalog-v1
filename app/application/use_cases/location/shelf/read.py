from uuid import UUID

from app.domain.entities import Shelf
from app.domain.repositories import BookcaseRepository, SectionRepository, ShelfRepository


async def _get_shelf_for_family(shelf_repo: ShelfRepository, section_repo: SectionRepository, bookcase_repo: BookcaseRepository, shelf_id: UUID, family_id: UUID) -> Shelf:
	from ..section.read import _get_section_for_family
	shelf = await shelf_repo.find_by_id(shelf_id)
	if shelf is None:
		raise LookupError("Shelf not found")
	await _get_section_for_family(section_repo, bookcase_repo, shelf.section_id, family_id)
	return shelf


class GetShelfUseCase:
	def __init__(self, shelf_repo: ShelfRepository, section_repo: SectionRepository, bookcase_repo: BookcaseRepository) -> None:
		self._shelf_repo = shelf_repo
		self._section_repo = section_repo
		self._bookcase_repo = bookcase_repo

	async def execute(self, shelf_id: UUID, family_id: UUID) -> Shelf:
		return await _get_shelf_for_family(self._shelf_repo, self._section_repo, self._bookcase_repo, shelf_id, family_id)
