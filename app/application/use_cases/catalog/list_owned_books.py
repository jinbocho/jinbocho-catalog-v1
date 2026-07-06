from uuid import UUID

from app.domain.entities import OwnedBook, ReadingStatus
from app.domain.repositories import BookReadRepository, OwnedBookRepository


class ListOwnedBooksUseCase:
	def __init__(self, book_repo: OwnedBookRepository, read_repo: BookReadRepository) -> None:
		self._book_repo = book_repo
		self._read_repo = read_repo

	async def execute(
		self,
		library_id: UUID,
		viewer_id: UUID,
		shelf_id: UUID | None = None,
		reading_status: ReadingStatus | None = None,
		tag: str | None = None,
		limit: int = 50,
		offset: int = 0,
	) -> list[OwnedBook]:
		books = await self._book_repo.find_all_by_library(
			library_id, shelf_id=shelf_id, reading_status=reading_status, tag=tag, limit=limit, offset=offset
		)
		read_ids = await self._read_repo.list_read_book_ids([b.id for b in books], viewer_id)
		for book in books:
			book.reading_status = book.reading_status_for(viewer_id, book.id in read_ids)
		return books
