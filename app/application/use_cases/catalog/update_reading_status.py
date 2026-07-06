import logging
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import BookEventType, BookHistory, OwnedBook, ReadingStatus
from app.domain.repositories import BookHistoryRepository, BookReadRepository, OwnedBookRepository
from app.utils import utcnow

logger = logging.getLogger(__name__)


@dataclass
class UpdateReadingStatusInput:
	book_id: UUID
	library_id: UUID
	changed_by: UUID
	reading_status: ReadingStatus


class UpdateReadingStatusUseCase:
	def __init__(
		self,
		book_repo: OwnedBookRepository,
		read_repo: BookReadRepository,
		history_repo: BookHistoryRepository,
	) -> None:
		self._book_repo = book_repo
		self._read_repo = read_repo
		self._history_repo = history_repo

	async def execute(self, inp: UpdateReadingStatusInput) -> OwnedBook:
		book = await self._book_repo.find_by_id(inp.book_id)
		if book is None:
			raise LookupError(f"OwnedBook {inp.book_id} not found")
		if book.library_id != inp.library_id:
			raise PermissionError("Access denied")

		old_status = book.reading_status_for(inp.changed_by, await self._read_repo.is_read(book.id, inp.changed_by))

		if inp.reading_status == ReadingStatus.READING:
			# Claiming the single physical copy — shared across the library by nature.
			book.current_reader_id = inp.changed_by
		else:
			# "Read"/"to_read" are personal: they only ever change whether
			# *this* caller has read it, never the whole library's view.
			if book.current_reader_id == inp.changed_by:
				book.current_reader_id = None
			if inp.reading_status == ReadingStatus.READ:
				await self._read_repo.add(book.id, inp.changed_by)
			else:
				await self._read_repo.remove(book.id, inp.changed_by)
		# The stored column only ever tracks "is anyone currently holding the
		# copy" now — "read" lives exclusively in BookRead, never here.
		book.reading_status = ReadingStatus.READING if book.current_reader_id is not None else ReadingStatus.TO_READ
		book.updated_at = utcnow()
		saved = await self._book_repo.save(book)
		new_status = saved.reading_status_for(inp.changed_by, await self._read_repo.is_read(saved.id, inp.changed_by))
		saved.reading_status = new_status
		await self._history_repo.save(
			BookHistory(
				owned_book_id=saved.id,
				event_type=BookEventType.READING_STATUS_CHANGED,
				changed_by=inp.changed_by,
				old_data={"reading_status": old_status},
				new_data={"reading_status": new_status},
				created_at=utcnow(),
			)
		)
		logger.info("Book %s reading status set to %s by library %s", saved.id, new_status, inp.library_id)
		return saved
