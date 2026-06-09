from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import BookHistory, OwnedBook
from app.domain.repositories import BookHistoryRepository, OwnedBookRepository
from app.utils import utcnow


@dataclass
class UpdateReadingStatusInput:
	book_id: UUID
	family_id: UUID
	changed_by: UUID
	reading_status: str


class UpdateReadingStatusUseCase:
	def __init__(self, book_repo: OwnedBookRepository, history_repo: BookHistoryRepository) -> None:
		self._book_repo = book_repo
		self._history_repo = history_repo

	async def execute(self, inp: UpdateReadingStatusInput) -> OwnedBook:
		book = await self._book_repo.find_by_id(inp.book_id)
		if book is None:
			raise LookupError(f"OwnedBook {inp.book_id} not found")
		if book.family_id != inp.family_id:
			raise PermissionError("Access denied")

		old_status = book.reading_status
		book.reading_status = inp.reading_status
		# Track who holds the copy: set on "reading", clear otherwise.
		book.current_reader_id = inp.changed_by if inp.reading_status == "reading" else None
		book.updated_at = utcnow()
		saved = await self._book_repo.save(book)
		await self._history_repo.save(
			BookHistory(
				owned_book_id=saved.id,
				event_type="reading_status_changed",
				changed_by=inp.changed_by,
				old_data={"reading_status": old_status},
				new_data={"reading_status": saved.reading_status},
				created_at=utcnow(),
			)
		)
		return saved
