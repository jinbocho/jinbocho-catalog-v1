from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import BibliographicRecord, OwnedBook
from app.domain.repositories import BibliographicRecordRepository, OwnedBookRepository


@dataclass
class ExportBookItem:
	book: OwnedBook
	record: BibliographicRecord | None


class ExportBooksUseCase:
	def __init__(self, book_repo: OwnedBookRepository, record_repo: BibliographicRecordRepository) -> None:
		self._book_repo = book_repo
		self._record_repo = record_repo

	async def execute(self, family_id: UUID, limit: int, offset: int) -> list[ExportBookItem]:
		books = await self._book_repo.find_all_by_family(family_id, limit=limit, offset=offset)
		record_map = {
			record.id: record
			for record in await self._record_repo.find_all_by_ids([book.bibliographic_record_id for book in books])
		}
		return [ExportBookItem(book=book, record=record_map.get(book.bibliographic_record_id)) for book in books]
