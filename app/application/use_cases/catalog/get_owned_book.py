from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import BibliographicRecord, OwnedBook
from app.domain.repositories import BibliographicRecordRepository, BookReadRepository, OwnedBookRepository


@dataclass
class GetOwnedBookOutput:
	book: OwnedBook
	record: BibliographicRecord


class GetOwnedBookUseCase:
	def __init__(
		self,
		book_repo: OwnedBookRepository,
		record_repo: BibliographicRecordRepository,
		read_repo: BookReadRepository,
	) -> None:
		self._book_repo = book_repo
		self._record_repo = record_repo
		self._read_repo = read_repo

	async def execute(self, book_id: UUID, family_id: UUID, viewer_id: UUID) -> GetOwnedBookOutput:
		book = await self._book_repo.find_by_id(book_id)
		if not book or book.family_id != family_id:
			raise LookupError("Book not found")
		record = await self._record_repo.find_by_id(book.bibliographic_record_id)
		if record is None:
			# bibliographic_record_id is FK RESTRICT — a missing record here means
			# the referential integrity invariant was violated, not a normal 404.
			raise LookupError("BibliographicRecord not found")
		has_read = await self._read_repo.is_read(book.id, viewer_id)
		book.reading_status = book.reading_status_for(viewer_id, has_read)
		return GetOwnedBookOutput(book=book, record=record)
