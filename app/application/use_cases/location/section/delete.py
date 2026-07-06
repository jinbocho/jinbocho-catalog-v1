import logging
from uuid import UUID

from app.domain.repositories import BookcaseRepository, SectionRepository

from .read import _get_section_for_library

logger = logging.getLogger(__name__)


class DeleteSectionUseCase:
	def __init__(self, section_repo: SectionRepository, bookcase_repo: BookcaseRepository) -> None:
		self._section_repo = section_repo
		self._bookcase_repo = bookcase_repo

	async def execute(self, section_id: UUID, library_id: UUID) -> None:
		await _get_section_for_library(self._section_repo, self._bookcase_repo, section_id, library_id)
		await self._section_repo.delete(section_id)
		logger.info("Section %s deleted from library %s", section_id, library_id)
