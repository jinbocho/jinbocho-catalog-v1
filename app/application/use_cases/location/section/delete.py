from uuid import UUID

from app.domain.repositories import BookcaseRepository, SectionRepository

from .read import _get_section_for_family


class DeleteSectionUseCase:
	def __init__(self, section_repo: SectionRepository, bookcase_repo: BookcaseRepository) -> None:
		self._section_repo = section_repo
		self._bookcase_repo = bookcase_repo

	async def execute(self, section_id: UUID, family_id: UUID) -> None:
		await _get_section_for_family(self._section_repo, self._bookcase_repo, section_id, family_id)
		await self._section_repo.delete(section_id)
