from uuid import UUID

from app.domain.entities import Shelf
from app.domain.repositories import BookcaseRepository, SectionRepository, ShelfRepository


class ListShelvesUseCase:
	def __init__(self, shelf_repo: ShelfRepository, section_repo: SectionRepository, bookcase_repo: BookcaseRepository) -> None:
		self._shelf_repo = shelf_repo
		self._section_repo = section_repo
		self._bookcase_repo = bookcase_repo

	async def execute(self, family_id: UUID, section_id: UUID | None = None, limit: int = 50, offset: int = 0) -> list[Shelf]:
		return await self._shelf_repo.find_all_by_family(family_id, section_id=section_id, limit=limit, offset=offset)
