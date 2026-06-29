from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.repositories import BibliographicRecordRepository, IsbnLookupCacheRepository
from app.utils import utcnow


@dataclass
class IncipitOutput:
	text: str | None
	source: str | None
	generated_at: datetime | None


class GetIncipitUseCase:
	"""Pure read: returns whatever incipit is already stored on the record.
	Never writes — callers can call this without a db.commit()."""

	def __init__(self, record_repo: BibliographicRecordRepository) -> None:
		self._record_repo = record_repo

	async def execute(self, record_id: UUID, family_id: UUID) -> IncipitOutput:
		record = await self._record_repo.find_by_id(record_id)
		if not record or record.family_id != family_id:
			raise LookupError("Bibliographic record not found")
		return IncipitOutput(record.incipit, record.incipit_source, record.incipit_generated_at)


class DeriveIncipitUseCase:
	"""Write path: looks up the ISBN cache for a free editorial description
	and, if found, persists it on the record.  Callers must commit after
	receiving a non-None result.text.

	Separated from GetIncipitUseCase to honour CQS — a GET endpoint should not
	commit to the database when the record already has an incipit."""

	def __init__(
		self,
		record_repo: BibliographicRecordRepository,
		cache_repo: IsbnLookupCacheRepository,
	) -> None:
		self._record_repo = record_repo
		self._cache_repo = cache_repo

	async def execute(self, record_id: UUID, family_id: UUID) -> IncipitOutput:
		record = await self._record_repo.find_by_id(record_id)
		if not record or record.family_id != family_id:
			raise LookupError("Bibliographic record not found")

		if record.isbn:
			cached = await self._cache_repo.find_by_isbn(record.isbn)
			# "description" is the canonical key (Open Library); "notes" is the
			# legacy key used by Google Books via volume_to_metadata.
			description = (cached.metadata.get("description") or cached.metadata.get("notes")) if cached else None
			if isinstance(description, str) and description.strip():
				record.incipit = description.strip()
				record.incipit_source = cached.source if cached else "isbn_lookup"
				record.incipit_generated_at = utcnow()
				record.updated_at = utcnow()
				saved = await self._record_repo.save(record)
				return IncipitOutput(saved.incipit, saved.incipit_source, saved.incipit_generated_at)

		return IncipitOutput(None, None, None)
