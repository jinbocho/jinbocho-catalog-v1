from uuid import UUID

from app.domain.entities import Bookcase
from app.domain.repositories import BookcaseRepository


async def _get_bookcase_for_library(bookcase_repo: BookcaseRepository, bookcase_id: UUID, library_id: UUID) -> Bookcase:
	bookcase = await bookcase_repo.find_by_id(bookcase_id)
	if bookcase is None:
		raise LookupError("Bookcase not found")
	if bookcase.library_id != library_id:
		raise PermissionError("Access denied")
	return bookcase


class GetBookcaseUseCase:
	def __init__(self, bookcase_repo: BookcaseRepository) -> None:
		self._bookcase_repo = bookcase_repo

	async def execute(self, bookcase_id: UUID, library_id: UUID) -> Bookcase:
		return await _get_bookcase_for_library(self._bookcase_repo, bookcase_id, library_id)
