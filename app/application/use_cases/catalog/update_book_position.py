from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import BookEventType, BookHistory, OwnedBook
from app.domain.repositories import BookHistoryRepository, OwnedBookRepository
from app.utils import utcnow


@dataclass
class UpdateBookPositionInput:
	book_id: UUID
	family_id: UUID
	changed_by: UUID
	room_id: UUID | None
	bookcase_id: UUID | None
	section_id: UUID | None
	shelf_id: UUID | None
	shelf_position: int | None
	position_description: str | None


class UpdateBookPositionUseCase:
	def __init__(self, book_repo: OwnedBookRepository, history_repo: BookHistoryRepository) -> None:
		self._book_repo = book_repo
		self._history_repo = history_repo

	async def execute(self, inp: UpdateBookPositionInput) -> OwnedBook:
		book = await self._book_repo.find_by_id(inp.book_id)
		if book is None:
			raise LookupError(f"OwnedBook {inp.book_id} not found")
		if book.family_id != inp.family_id:
			raise PermissionError("Access denied")

		old = {
			"room_id": str(book.room_id) if book.room_id else None,
			"bookcase_id": str(book.bookcase_id) if book.bookcase_id else None,
			"section_id": str(book.section_id) if book.section_id else None,
			"shelf_id": str(book.shelf_id) if book.shelf_id else None,
			"shelf_position": book.shelf_position,
			"position_description": book.position_description,
		}
		book.room_id = inp.room_id
		book.bookcase_id = inp.bookcase_id
		book.section_id = inp.section_id
		book.shelf_id = inp.shelf_id
		book.shelf_position = inp.shelf_position
		book.position_description = inp.position_description
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
					"position_description": saved.position_description,
				},
				created_at=utcnow(),
			)
		)
		return saved
