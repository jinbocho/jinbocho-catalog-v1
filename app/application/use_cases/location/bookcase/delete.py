import logging
from uuid import UUID

from app.domain.repositories import BookcaseRepository

from .read import _get_bookcase_for_library

logger = logging.getLogger(__name__)


class DeleteBookcaseUseCase:
	def __init__(self, bookcase_repo: BookcaseRepository) -> None:
		self._bookcase_repo = bookcase_repo

	async def execute(self, bookcase_id: UUID, library_id: UUID) -> None:
		await _get_bookcase_for_library(self._bookcase_repo, bookcase_id, library_id)
		await self._bookcase_repo.delete(bookcase_id)
		logger.info("Bookcase %s deleted from library %s", bookcase_id, library_id)
