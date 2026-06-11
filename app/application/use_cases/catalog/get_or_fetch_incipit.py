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


class GetOrFetchIncipitUseCase:
	"""Resolve a book's "presentation" text without any AI dependency.

	Order: stored value → free editorial description cached at ISBN lookup. When neither
	is available it returns an empty result so the AI layer (optional) can step in later.
	"""

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

		if record.incipit:
			return IncipitOutput(record.incipit, record.incipit_source, record.incipit_generated_at)

		if record.isbn:
			cached = await self._cache_repo.find_by_isbn(record.isbn)
			description = cached.metadata.get("notes") if cached else None
			if isinstance(description, str) and description.strip():
				record.incipit = description.strip()
				record.incipit_source = cached.source if cached else "isbn_lookup"
				record.incipit_generated_at = utcnow()
				record.updated_at = utcnow()
				saved = await self._record_repo.save(record)
				return IncipitOutput(saved.incipit, saved.incipit_source, saved.incipit_generated_at)

		return IncipitOutput(None, None, None)
