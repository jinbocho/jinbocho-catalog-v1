from uuid import UUID

from app.domain.entities import BookHistory
from app.domain.repositories import BookHistoryRepository, OwnedBookRepository


class GetBookHistoryUseCase:
	def __init__(self, history_repo: BookHistoryRepository, book_repo: OwnedBookRepository) -> None:
		self._history_repo = history_repo
		self._book_repo = book_repo

	async def execute(self, book_id: UUID, family_id: UUID, limit: int = 50, offset: int = 0) -> list[BookHistory]:
		book = await self._book_repo.find_by_id(book_id)
		if not book:
			raise LookupError("Book not found")
		if book.family_id != family_id:
			raise PermissionError("Book does not belong to this family")
		return await self._history_repo.find_by_book(book_id, limit=limit, offset=offset)
