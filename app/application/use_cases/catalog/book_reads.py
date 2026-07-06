import logging
from datetime import datetime
from uuid import UUID

from app.domain.entities import BookRead
from app.domain.repositories import BookReadRepository, OwnedBookRepository

logger = logging.getLogger(__name__)


class MarkBookReadUseCase:
    def __init__(self, book_repo: OwnedBookRepository, read_repo: BookReadRepository) -> None:
        self._book_repo = book_repo
        self._read_repo = read_repo

    async def execute(
        self, book_id: UUID, library_id: UUID, user_id: UUID, read_at: datetime | None = None
    ) -> BookRead:
        book = await self._book_repo.find_by_id(book_id)
        if not book:
            raise LookupError("Book not found")
        if book.library_id != library_id:
            raise PermissionError("Book does not belong to this library")
        saved = await self._read_repo.add(book_id, user_id, read_at)
        logger.info("Book %s marked read by user %s in library %s", book_id, user_id, library_id)
        return saved


class UnmarkBookReadUseCase:
    def __init__(self, book_repo: OwnedBookRepository, read_repo: BookReadRepository) -> None:
        self._book_repo = book_repo
        self._read_repo = read_repo

    async def execute(self, book_id: UUID, library_id: UUID, user_id: UUID) -> None:
        book = await self._book_repo.find_by_id(book_id)
        if not book:
            raise LookupError("Book not found")
        if book.library_id != library_id:
            raise PermissionError("Book does not belong to this library")
        await self._read_repo.remove(book_id, user_id)
        logger.info("Book %s unmarked read by user %s in library %s", book_id, user_id, library_id)


class ListBookReadsUseCase:
    def __init__(self, book_repo: OwnedBookRepository, read_repo: BookReadRepository) -> None:
        self._book_repo = book_repo
        self._read_repo = read_repo

    async def execute(self, book_id: UUID, library_id: UUID) -> list[BookRead]:
        book = await self._book_repo.find_by_id(book_id)
        if not book:
            raise LookupError("Book not found")
        if book.library_id != library_id:
            raise PermissionError("Book does not belong to this library")
        return await self._read_repo.list_by_book(book_id)


class ListLibraryReadsUseCase:
    def __init__(self, read_repo: BookReadRepository) -> None:
        self._read_repo = read_repo

    async def execute(self, library_id: UUID) -> list[BookRead]:
        return await self._read_repo.list_by_library(library_id)
