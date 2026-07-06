from uuid import UUID

from app.domain.entities import BibliographicRecord
from app.domain.repositories import BibliographicRecordRepository


class GetBibliographicRecordUseCase:
	def __init__(self, record_repo: BibliographicRecordRepository) -> None:
		self._record_repo = record_repo

	async def execute(self, record_id: UUID, library_id: UUID) -> BibliographicRecord:
		record = await self._record_repo.find_by_id(record_id)
		if not record:
			raise LookupError("Bibliographic record not found")
		if record.library_id != library_id:
			raise PermissionError("Bibliographic record does not belong to this library")
		return record
