import logging
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import BookEventType, BookHistory
from app.domain.repositories import BookHistoryRepository, OwnedBookRepository
from app.utils import utcnow

logger = logging.getLogger(__name__)


@dataclass
class BulkDeleteBooksInput:
	book_ids: list[UUID]
	family_id: UUID
	changed_by: UUID


class BulkDeleteBooksUseCase:
	def __init__(self, book_repo: OwnedBookRepository, history_repo: BookHistoryRepository) -> None:
		self._book_repo = book_repo
		self._history_repo = history_repo

	async def execute(self, inp: BulkDeleteBooksInput) -> int:
		requested_ids = list(dict.fromkeys(inp.book_ids))
		books = await self._book_repo.find_by_ids(requested_ids)
		books_by_id = {book.id: book for book in books}

		missing_ids = [book_id for book_id in requested_ids if book_id not in books_by_id]
		if missing_ids:
			raise LookupError(f"OwnedBook(s) not found: {missing_ids}")

		foreign_ids = [book.id for book in books if book.family_id != inp.family_id]
		if foreign_ids:
			raise PermissionError("Access denied")

		for book_id in requested_ids:
			book = books_by_id[book_id]
			await self._history_repo.save(
				BookHistory(
					owned_book_id=book.id,
					event_type=BookEventType.DELETED,
					changed_by=inp.changed_by,
					old_data={"bibliographic_record_id": str(book.bibliographic_record_id)},
					created_at=utcnow(),
				)
			)
		await self._book_repo.delete_by_ids(requested_ids)
		logger.info("Bulk-deleted %d books from family %s", len(requested_ids), inp.family_id)
		return len(requested_ids)
