from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import BookEventType, BookHistory
from app.domain.repositories import BookHistoryRepository, OwnedBookRepository
from app.utils import utcnow


@dataclass
class DeleteBookInput:
	book_id: UUID
	family_id: UUID
	changed_by: UUID


class DeleteBookUseCase:
	def __init__(self, book_repo: OwnedBookRepository, history_repo: BookHistoryRepository) -> None:
		self._book_repo = book_repo
		self._history_repo = history_repo

	async def execute(self, inp: DeleteBookInput) -> None:
		book = await self._book_repo.find_by_id(inp.book_id)
		if book is None:
			raise LookupError(f"OwnedBook {inp.book_id} not found")
		if book.family_id != inp.family_id:
			raise PermissionError("Access denied")
		await self._history_repo.save(
			BookHistory(
				owned_book_id=book.id,
				event_type=BookEventType.DELETED,
				changed_by=inp.changed_by,
				old_data={"bibliographic_record_id": str(book.bibliographic_record_id)},
				created_at=utcnow(),
			)
		)
		await self._book_repo.delete(book.id)
