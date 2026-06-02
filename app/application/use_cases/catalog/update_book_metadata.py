from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.domain.entities import OwnedBook
from app.domain.repositories import BookHistoryRepository, OwnedBookRepository
from app.utils import utcnow


@dataclass
class UpdateBookMetadataInput:
	book_id: UUID
	family_id: UUID
	changed_by: UUID
	condition: str | None = None
	purchase_date: date | None = None
	purchase_price: Decimal | None = None
	source: str | None = None
	reading_status: str | None = None
	tags: list[str] | None = None
	notes: str | None = None


class UpdateBookMetadataUseCase:
	def __init__(self, book_repo: OwnedBookRepository, history_repo: BookHistoryRepository) -> None:
		self._book_repo = book_repo
		self._history_repo = history_repo

	async def execute(self, inp: UpdateBookMetadataInput) -> OwnedBook:
		book = await self._book_repo.find_by_id(inp.book_id)
		if not book or book.family_id != inp.family_id:
			raise LookupError("Book not found")
		if inp.condition is not None:
			book.condition = inp.condition
		if inp.purchase_date is not None:
			book.purchase_date = inp.purchase_date
		if inp.purchase_price is not None:
			book.purchase_price = inp.purchase_price
		if inp.source is not None:
			book.source = inp.source
		if inp.reading_status is not None:
			book.reading_status = inp.reading_status
		if inp.tags is not None:
			book.tags = inp.tags
		if inp.notes is not None:
			book.notes = inp.notes
		book.updated_at = utcnow()
		updated = await self._book_repo.save(book)
		await self._history_repo.save(
			BookHistory(
				owned_book_id=book.id, event_type="metadata_updated", changed_by=inp.changed_by, created_at=utcnow()
			)
		)
		return updated
