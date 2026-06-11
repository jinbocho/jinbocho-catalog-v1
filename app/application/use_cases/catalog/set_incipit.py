from uuid import UUID

from app.application.use_cases.catalog.get_or_fetch_incipit import IncipitOutput
from app.domain.repositories import BibliographicRecordRepository
from app.utils import utcnow

_ALLOWED_SOURCES = {"manual", "ai"}


class SetIncipitUseCase:
	"""Persist a presentation text supplied by the user (manual) or by the AI service (ai)."""

	def __init__(self, record_repo: BibliographicRecordRepository) -> None:
		self._record_repo = record_repo

	async def execute(self, record_id: UUID, family_id: UUID, text: str, source: str) -> IncipitOutput:
		if source not in _ALLOWED_SOURCES:
			raise ValueError(f"Invalid incipit source: {source}")

		record = await self._record_repo.find_by_id(record_id)
		if not record or record.family_id != family_id:
			raise LookupError("Bibliographic record not found")

		record.incipit = text.strip()
		record.incipit_source = source
		record.incipit_generated_at = utcnow()
		record.updated_at = utcnow()
		saved = await self._record_repo.save(record)
		return IncipitOutput(saved.incipit, saved.incipit_source, saved.incipit_generated_at)
