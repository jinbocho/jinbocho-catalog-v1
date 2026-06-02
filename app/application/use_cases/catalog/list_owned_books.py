from uuid import UUID

from app.domain.entities import OwnedBook
from app.domain.repositories import OwnedBookRepository


class ListOwnedBooksUseCase:
	def __init__(self, book_repo: OwnedBookRepository) -> None:
		self._book_repo = book_repo

	async def execute(
		self, family_id: UUID, shelf_id: UUID | None = None, reading_status: str | None = None, tag: str | None = None, limit: int = 50, offset: int = 0
	) -> list[OwnedBook]:
		return await self._book_repo.find_all_by_family(
			family_id, shelf_id=shelf_id, reading_status=reading_status, tag=tag, limit=limit, offset=offset
		)
