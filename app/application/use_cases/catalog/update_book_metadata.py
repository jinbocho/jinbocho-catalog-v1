import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.domain.entities import (
	BookCondition,
	BookEventType,
	BookHistory,
	BookSource,
	OwnedBook,
	ReadingStatus,
)
from app.domain.repositories import BookHistoryRepository, BookReadRepository, OwnedBookRepository
from app.utils import utcnow

logger = logging.getLogger(__name__)


@dataclass
class UpdateBookMetadataInput:
	book_id: UUID
	library_id: UUID
	changed_by: UUID
	condition: BookCondition | None = None
	purchase_date: date | None = None
	purchase_price: Decimal | None = None
	source: BookSource | None = None
	reading_status: ReadingStatus | None = None
	owner_id: UUID | None = None
	tags: list[str] | None = None
	notes: str | None = None


class UpdateBookMetadataUseCase:
	def __init__(
		self,
		book_repo: OwnedBookRepository,
		read_repo: BookReadRepository,
		history_repo: BookHistoryRepository,
	) -> None:
		self._book_repo = book_repo
		self._read_repo = read_repo
		self._history_repo = history_repo

	async def execute(self, inp: UpdateBookMetadataInput) -> OwnedBook:
		book = await self._book_repo.find_by_id(inp.book_id)
		if not book:
			raise LookupError("Book not found")
		if book.library_id != inp.library_id:
			raise PermissionError("Book does not belong to this library")
		if inp.condition is not None:
			book.condition = inp.condition
		if inp.purchase_date is not None:
			book.purchase_date = inp.purchase_date
		if inp.purchase_price is not None:
			book.purchase_price = inp.purchase_price
		if inp.source is not None:
			book.source = inp.source
		if inp.reading_status is not None:
			# Mirror the same per-member rule as UpdateReadingStatusUseCase:
			# "reading" claims the shared copy, "read"/"to_read" only ever
			# affect this caller's own BookRead row.
			if inp.reading_status == ReadingStatus.READING:
				book.current_reader_id = inp.changed_by
			else:
				if book.current_reader_id == inp.changed_by:
					book.current_reader_id = None
				if inp.reading_status == ReadingStatus.READ:
					await self._read_repo.add(book.id, inp.changed_by)
				else:
					await self._read_repo.remove(book.id, inp.changed_by)
			book.reading_status = ReadingStatus.READING if book.current_reader_id is not None else ReadingStatus.TO_READ
		if inp.owner_id is not None:
			book.owner_id = inp.owner_id
		if inp.tags is not None:
			book.tags = inp.tags
		if inp.notes is not None:
			book.notes = inp.notes
		book.updated_at = utcnow()
		updated = await self._book_repo.save(book)
		if inp.reading_status is not None:
			has_read = await self._read_repo.is_read(updated.id, inp.changed_by)
			updated.reading_status = updated.reading_status_for(inp.changed_by, has_read)
		await self._history_repo.save(
			BookHistory(
				owned_book_id=book.id,
					event_type=BookEventType.METADATA_UPDATED,
					changed_by=inp.changed_by,
					created_at=utcnow(),
			)
		)
		logger.info("Book %s metadata updated by library %s", book.id, inp.library_id)
		return updated
