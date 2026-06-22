from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import BibliographicRecord, map_to_genre
from app.domain.repositories import BibliographicRecordRepository
from app.utils import utcnow


@dataclass
class CreateBibliographicRecordInput:
	family_id: UUID
	title: str
	main_author: str | None = None
	other_authors: list[str] | None = None
	isbn: str | None = None
	publisher: str | None = None
	publication_year: int | None = None
	language: str | None = None
	genre: str | None = None
	cover_url: str | None = None
	notes: str | None = None


class CreateBibliographicRecordUseCase:
	def __init__(self, record_repo: BibliographicRecordRepository) -> None:
		self._record_repo = record_repo

	async def execute(self, inp: CreateBibliographicRecordInput) -> BibliographicRecord:
		# The DB enforces UNIQUE(family_id, isbn); a blind insert would crash
		# with a generic 409 "data integrity violation" the second time someone
		# adds a book with an ISBN the family already has on file. Reuse the
		# existing record instead — same rule AddBookUseCase already applies
		# when it resolves a record by ISBN internally.
		# Note: unlike AddBookUseCase's own internal resolution path, this use
		# case stores isbn exactly as given (no normalize_isbn) — match that
		# here too, or a hyphenated resubmission of the same ISBN wouldn't be
		# found and would still crash on the unique constraint.
		if inp.isbn:
			existing = await self._record_repo.find_by_isbn(inp.family_id, inp.isbn)
			if existing:
				return existing

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
