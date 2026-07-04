from uuid import UUID

from app.domain.entities import Section
from app.domain.repositories import BookcaseRepository, SectionRepository

from ..bookcase.read import _get_bookcase_for_family


async def _get_section_for_family(
	section_repo: SectionRepository, bookcase_repo: BookcaseRepository, section_id: UUID, family_id: UUID
) -> Section:
	section = await section_repo.find_by_id(section_id)
	if section is None:
		raise LookupError("Section not found")
	await _get_bookcase_for_family(bookcase_repo, section.bookcase_id, family_id)
	return section


class GetSectionUseCase:
	def __init__(self, section_repo: SectionRepository, bookcase_repo: BookcaseRepository) -> None:
		self._section_repo = section_repo
		self._bookcase_repo = bookcase_repo

	async def execute(self, section_id: UUID, family_id: UUID) -> Section:
		return await _get_section_for_family(self._section_repo, self._bookcase_repo, section_id, family_id)
