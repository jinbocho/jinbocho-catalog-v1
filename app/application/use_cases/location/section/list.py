from uuid import UUID

from app.domain.entities import Section
from app.domain.repositories import BookcaseRepository, SectionRepository

from ..bookcase.read import _get_bookcase_for_family


class ListSectionsUseCase:
	def __init__(self, section_repo: SectionRepository, bookcase_repo: BookcaseRepository) -> None:
		self._section_repo = section_repo
		self._bookcase_repo = bookcase_repo

	async def execute(self, family_id: UUID, bookcase_id: UUID | None = None, limit: int = 50, offset: int = 0) -> list[Section]:
		if bookcase_id is not None:
			await _get_bookcase_for_family(self._bookcase_repo, bookcase_id, family_id)
		return await self._section_repo.find_all_by_family(family_id, bookcase_id=bookcase_id, limit=limit, offset=offset)
