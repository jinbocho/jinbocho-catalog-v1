from dataclasses import dataclass
from uuid import UUID

from app.domain.repositories import BibliographicRecordRepository


@dataclass
class GenreCount:
	genre: str
	count: int


class ListGenresUseCase:
	def __init__(self, record_repo: BibliographicRecordRepository) -> None:
		self._record_repo = record_repo

	async def execute(self, family_id: UUID) -> list[GenreCount]:
		counts = await self._record_repo.count_genres(family_id)
		return [GenreCount(genre=genre, count=count) for genre, count in counts]
