import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.application.services import GoodreadsRow, parse_goodreads_csv
from app.domain.entities import ReadingStatus
from app.domain.repositories import BibliographicRecordRepository, OwnedBookRepository

GoodreadsPreviewRowStatus = Literal["new", "already_owned", "invalid"]


@dataclass
class PreviewGoodreadsImportInput:
	library_id: UUID
	csv_text: str


@dataclass
class GoodreadsPreviewRow:
	row_number: int
	status: GoodreadsPreviewRowStatus
	title: str
	main_author: str | None
	other_authors: list[str]
	isbn: str | None
	publisher: str | None
	publication_year: int | None
	reading_status: ReadingStatus
	rating: int | None
	review: str | None
	read_at: datetime | None
	tags: list[str]


@dataclass
class PreviewGoodreadsImportOutput:
	rows: list[GoodreadsPreviewRow]


class PreviewGoodreadsImportUseCase:
	"""Parses the CSV and classifies each row without writing anything —
	mirrors ScanShelfUseCase's dry-run preview so the FE can show the same
	review-before-commit pattern the user already knows from shelf scan."""

	def __init__(self, record_repo: BibliographicRecordRepository, book_repo: OwnedBookRepository) -> None:
		self._record_repo = record_repo
		self._book_repo = book_repo

	async def execute(self, inp: PreviewGoodreadsImportInput) -> PreviewGoodreadsImportOutput:
		rows = parse_goodreads_csv(inp.csv_text)
		# One library-scoped read per row; a Goodreads export can be hundreds of
		# rows, so these run concurrently rather than serially awaited.
		previewed = await asyncio.gather(*(self._to_preview_row(inp.library_id, row) for row in rows))
		return PreviewGoodreadsImportOutput(rows=list(previewed))

	async def _to_preview_row(self, library_id: UUID, row: GoodreadsRow) -> GoodreadsPreviewRow:
		status: GoodreadsPreviewRowStatus = "invalid" if not row.title else "new"
		if status == "new" and await self._is_already_owned(library_id, row):
			status = "already_owned"
		return GoodreadsPreviewRow(
			row_number=row.row_number,
			status=status,
			title=row.title,
			main_author=row.main_author,
			other_authors=row.other_authors,
			isbn=row.isbn,
			publisher=row.publisher,
			publication_year=row.publication_year,
			reading_status=row.reading_status,
			rating=row.rating,
			review=row.review,
			read_at=row.read_at,
			tags=row.tags,
		)

	async def _is_already_owned(self, library_id: UUID, row: GoodreadsRow) -> bool:
		record = await self._record_repo.find_by_isbn(library_id, row.isbn) if row.isbn else None
		if record is None:
			record = await self._record_repo.find_by_title_author(library_id, row.title, row.main_author)
		if record is None:
			return False
		return await self._book_repo.exists_by_bibliographic_record_id(record.id)
