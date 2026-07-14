import logging
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import BookEventType, BookHistory
from app.domain.repositories import BookHistoryRepository, OwnedBookRepository
from app.utils import utcnow

logger = logging.getLogger(__name__)


@dataclass
class BulkMoveBooksInput:
	book_ids: list[UUID]
	library_id: UUID
	changed_by: UUID
	room_id: UUID | None
	bookcase_id: UUID | None
	section_id: UUID | None
	shelf_id: UUID | None
	shelf_position: int | None


class BulkMoveBooksUseCase:
	def __init__(self, book_repo: OwnedBookRepository, history_repo: BookHistoryRepository) -> None:
		self._book_repo = book_repo
		self._history_repo = history_repo

	async def execute(self, inp: BulkMoveBooksInput) -> int:
		requested_ids = list(dict.fromkeys(inp.book_ids))
		books = await self._book_repo.find_by_ids(requested_ids)
		books_by_id = {book.id: book for book in books}

		missing_ids = [book_id for book_id in requested_ids if book_id not in books_by_id]
		if missing_ids:
			raise LookupError(f"OwnedBook(s) not found: {missing_ids}")

		foreign_ids = [book.id for book in books if book.library_id != inp.library_id]
		if foreign_ids:
			raise PermissionError("Access denied")

		for book_id in requested_ids:
			book = books_by_id[book_id]
			old = {
				"room_id": str(book.room_id) if book.room_id else None,
				"bookcase_id": str(book.bookcase_id) if book.bookcase_id else None,
				"section_id": str(book.section_id) if book.section_id else None,
				"shelf_id": str(book.shelf_id) if book.shelf_id else None,
				"shelf_position": book.shelf_position,
			}
			book.room_id = inp.room_id
			book.bookcase_id = inp.bookcase_id
			book.section_id = inp.section_id
			book.shelf_id = inp.shelf_id
			book.shelf_position = inp.shelf_position
			book.updated_at = utcnow()
			saved = await self._book_repo.save(book)
			await self._history_repo.save(
				BookHistory(
					owned_book_id=saved.id,
					event_type=BookEventType.POSITION_CHANGED,
					changed_by=inp.changed_by,
					old_data=old,
					new_data={
						"room_id": str(saved.room_id) if saved.room_id else None,
						"bookcase_id": str(saved.bookcase_id) if saved.bookcase_id else None,
						"section_id": str(saved.section_id) if saved.section_id else None,
						"shelf_id": str(saved.shelf_id) if saved.shelf_id else None,
						"shelf_position": saved.shelf_position,
					},
					created_at=utcnow(),
				)
			)

		logger.info("Bulk-moved %d books to a new position in library %s", len(requested_ids), inp.library_id)
		return len(requested_ids)
