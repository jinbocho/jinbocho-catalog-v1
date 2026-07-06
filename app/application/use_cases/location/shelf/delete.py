import logging
from uuid import UUID

from app.domain.repositories import BookcaseRepository, SectionRepository, ShelfRepository

from .read import _get_shelf_for_library

logger = logging.getLogger(__name__)


class DeleteShelfUseCase:
	def __init__(
		self, shelf_repo: ShelfRepository, section_repo: SectionRepository, bookcase_repo: BookcaseRepository
	) -> None:
		self._shelf_repo = shelf_repo
		self._section_repo = section_repo
		self._bookcase_repo = bookcase_repo

	async def execute(self, shelf_id: UUID, library_id: UUID) -> None:
		await _get_shelf_for_library(
			self._shelf_repo, self._section_repo, self._bookcase_repo, shelf_id, library_id
		)
		await self._shelf_repo.delete(shelf_id)
		logger.info("Shelf %s deleted from library %s", shelf_id, library_id)
