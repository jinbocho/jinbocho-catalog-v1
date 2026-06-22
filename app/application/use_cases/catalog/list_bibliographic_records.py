from uuid import UUID

from app.domain.entities import BibliographicRecord
from app.domain.repositories import BibliographicRecordRepository


class ListBibliographicRecordsUseCase:
	def __init__(self, record_repo: BibliographicRecordRepository) -> None:
		self._record_repo = record_repo

	async def execute(
		self,
		family_id: UUID,
		q: str | None,
		genre: str | None,
		limit: int,
		offset: int,
	) -> list[BibliographicRecord]:
		return await self._record_repo.find_all_by_family(family_id, q=q, genre=genre, limit=limit, offset=offset)
