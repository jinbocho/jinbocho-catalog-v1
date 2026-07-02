import logging
from uuid import UUID

from app.domain.repositories import BibliographicRecordRepository, OwnedBookRepository

logger = logging.getLogger(__name__)


class DeleteBibliographicRecordUseCase:
	def __init__(self, record_repo: BibliographicRecordRepository, book_repo: OwnedBookRepository) -> None:
		self._record_repo = record_repo
		self._book_repo = book_repo

	async def execute(self, record_id: UUID, family_id: UUID) -> None:
		record = await self._record_repo.find_by_id(record_id)
		if record is None:
			raise LookupError("Bibliographic record not found")
		if record.family_id != family_id:
			raise PermissionError("Access denied")

		if await self._book_repo.exists_by_bibliographic_record_id(record_id):
			raise ValueError("Cannot delete a bibliographic record that is still referenced by owned books")
		await self._record_repo.delete(record_id)
		logger.info("Bibliographic record %s deleted from family %s", record_id, family_id)
