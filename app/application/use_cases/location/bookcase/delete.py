import logging
from uuid import UUID

from app.domain.repositories import BookcaseRepository

from .read import _get_bookcase_for_family

logger = logging.getLogger(__name__)


class DeleteBookcaseUseCase:
	def __init__(self, bookcase_repo: BookcaseRepository) -> None:
		self._bookcase_repo = bookcase_repo

	async def execute(self, bookcase_id: UUID, family_id: UUID) -> None:
		await _get_bookcase_for_family(self._bookcase_repo, bookcase_id, family_id)
		await self._bookcase_repo.delete(bookcase_id)
		logger.info("Bookcase %s deleted from family %s", bookcase_id, family_id)
