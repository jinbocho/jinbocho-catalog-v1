from datetime import datetime
from uuid import UUID

from app.domain.entities import BookRead
from app.domain.repositories import BookReadRepository, OwnedBookRepository


class MarkBookReadUseCase:
    def __init__(self, book_repo: OwnedBookRepository, read_repo: BookReadRepository) -> None:
        self._book_repo = book_repo
        self._read_repo = read_repo

    async def execute(self, book_id: UUID, family_id: UUID, user_id: UUID, read_at: datetime | None = None) -> BookRead:
        book = await self._book_repo.find_by_id(book_id)
        if not book or book.family_id != family_id:
            raise LookupError("Book not found")
        return await self._read_repo.add(book_id, user_id, read_at)


class UnmarkBookReadUseCase:
    def __init__(self, book_repo: OwnedBookRepository, read_repo: BookReadRepository) -> None:
        self._book_repo = book_repo
        self._read_repo = read_repo

    async def execute(self, book_id: UUID, family_id: UUID, user_id: UUID) -> None:
        book = await self._book_repo.find_by_id(book_id)
        if not book or book.family_id != family_id:
            raise LookupError("Book not found")
        await self._read_repo.remove(book_id, user_id)


class ListBookReadsUseCase:
    def __init__(self, book_repo: OwnedBookRepository, read_repo: BookReadRepository) -> None:
        self._book_repo = book_repo
        self._read_repo = read_repo

    async def execute(self, book_id: UUID, family_id: UUID) -> list[BookRead]:
        book = await self._book_repo.find_by_id(book_id)
        if not book or book.family_id != family_id:
            raise LookupError("Book not found")
        return await self._read_repo.list_by_book(book_id)


class ListFamilyReadsUseCase:
    def __init__(self, read_repo: BookReadRepository) -> None:
        self._read_repo = read_repo

    async def execute(self, family_id: UUID) -> list[BookRead]:
        return await self._read_repo.list_by_family(family_id)
