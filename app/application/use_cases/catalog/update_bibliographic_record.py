from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from app.domain.entities import BibliographicRecord, map_to_genre
from app.domain.repositories import BibliographicRecordRepository
from app.utils import utcnow


@dataclass
class UpdateBibliographicRecordInput:
	record_id: UUID
	family_id: UUID
	title: Optional[str] = None
	main_author: Optional[str] = None
	other_authors: list[str] | None = None
	isbn: Optional[str] = None
	publisher: Optional[str] = None
	publication_year: Optional[int] = None
	language: Optional[str] = None
	genre: Optional[str] = None
	cover_url: Optional[str] = None
	notes: Optional[str] = None


class UpdateBibliographicRecordUseCase:
	def __init__(self, record_repo: BibliographicRecordRepository) -> None:
		self._record_repo = record_repo

	async def execute(self, inp: UpdateBibliographicRecordInput) -> BibliographicRecord:
		record = await self._record_repo.find_by_id(inp.record_id)
		if record is None:
			raise LookupError("Bibliographic record not found")
		if record.family_id != inp.family_id:
			raise PermissionError("Access denied")

		if inp.title is not None:
			record.title = inp.title
		if inp.main_author is not None:
			record.main_author = inp.main_author
		if inp.other_authors is not None:
			record.other_authors = inp.other_authors
		if inp.isbn is not None:
			record.isbn = inp.isbn
		if inp.publisher is not None:
			record.publisher = inp.publisher
		if inp.publication_year is not None:
			record.publication_year = inp.publication_year
		if inp.language is not None:
			record.language = inp.language
		if inp.genre is not None:
			genre = map_to_genre(inp.genre)
			record.genre = genre.value if genre else None
			record.genre_raw = inp.genre
		if inp.cover_url is not None:
			record.cover_url = inp.cover_url
		if inp.notes is not None:
			record.notes = inp.notes
		record.updated_at = utcnow()
		return await self._record_repo.save(record)
