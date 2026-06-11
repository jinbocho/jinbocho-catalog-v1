from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from app.domain.entities import BibliographicRecord, map_to_genre
from app.domain.repositories import BibliographicRecordRepository
from app.utils import utcnow


@dataclass
class CreateBibliographicRecordInput:
	family_id: UUID
	title: str
	main_author: Optional[str] = None
	other_authors: list[str] | None = None
	isbn: Optional[str] = None
	publisher: Optional[str] = None
	publication_year: Optional[int] = None
	language: Optional[str] = None
	genre: Optional[str] = None
	cover_url: Optional[str] = None
	notes: Optional[str] = None


class CreateBibliographicRecordUseCase:
	def __init__(self, record_repo: BibliographicRecordRepository) -> None:
		self._record_repo = record_repo

	async def execute(self, inp: CreateBibliographicRecordInput) -> BibliographicRecord:
		genre = map_to_genre(inp.genre)
		return await self._record_repo.save(
			BibliographicRecord(
				family_id=inp.family_id,
				title=inp.title,
				main_author=inp.main_author,
				other_authors=inp.other_authors or [],
				isbn=inp.isbn,
				publisher=inp.publisher,
				publication_year=inp.publication_year,
				language=inp.language,
				genre=genre.value if genre else None,
				genre_raw=inp.genre,
				cover_url=inp.cover_url,
				notes=inp.notes,
				created_at=utcnow(),
				updated_at=utcnow(),
			)
		)
