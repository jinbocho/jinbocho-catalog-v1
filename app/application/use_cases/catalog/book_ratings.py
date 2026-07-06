import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.domain.entities import BookRating, LibraryRatingStats
from app.domain.repositories import BookRatingRepository, OwnedBookRepository

logger = logging.getLogger(__name__)


@dataclass
class CreateBookRatingInput:
    book_id: UUID
    library_id: UUID
    user_id: UUID
    rating: int
    review: str | None = None


@dataclass
class UpdateBookRatingInput:
    rating_id: UUID
    book_id: UUID
    library_id: UUID
    user_id: UUID
    rating: int | None = None
    review: str | None = None


class CreateBookRatingUseCase:
    def __init__(self, book_repo: OwnedBookRepository, rating_repo: BookRatingRepository) -> None:
        self._book_repo = book_repo
        self._rating_repo = rating_repo

    async def execute(self, inp: CreateBookRatingInput) -> BookRating:
        book = await self._book_repo.find_by_id(inp.book_id)
        if not book:
            raise LookupError("Book not found")
        if book.library_id != inp.library_id:
            raise PermissionError("Book does not belong to this library")
        existing = await self._rating_repo.find_by_book_and_user(inp.book_id, inp.user_id)
        if existing is not None:
            raise ValueError("You have already rated this book")
        saved = await self._rating_repo.add(
            BookRating(
                owned_book_id=inp.book_id,
                user_id=inp.user_id,
                rating=inp.rating,
                review=inp.review,
            )
        )
        logger.info("Book %s rated by library %s", inp.book_id, inp.library_id)
        return saved


class UpdateBookRatingUseCase:
    def __init__(self, book_repo: OwnedBookRepository, rating_repo: BookRatingRepository) -> None:
        self._book_repo = book_repo
        self._rating_repo = rating_repo

    async def execute(self, inp: UpdateBookRatingInput) -> BookRating:
        rating = await self._rating_repo.find_by_id(inp.rating_id)
        if rating is None:
            raise LookupError("Rating not found")
        book = await self._book_repo.find_by_id(inp.book_id)
        if not book:
            raise LookupError("Book not found")
        if book.library_id != inp.library_id:
            raise PermissionError("Book does not belong to this library")
        if rating.user_id != inp.user_id:
            raise PermissionError("Cannot modify another user's rating")
        if inp.rating is not None:
            rating.rating = inp.rating
            if not 1 <= rating.rating <= 5:
                raise ValueError("rating must be between 1 and 5")
        if inp.review is not None:
            rating.review = inp.review
        rating.updated_at = datetime.now(UTC)
        saved = await self._rating_repo.save(rating)
        logger.info("Book %s rating %s updated by library %s", inp.book_id, inp.rating_id, inp.library_id)
        return saved


class DeleteBookRatingUseCase:
    def __init__(self, book_repo: OwnedBookRepository, rating_repo: BookRatingRepository) -> None:
        self._book_repo = book_repo
        self._rating_repo = rating_repo

    async def execute(self, rating_id: UUID, library_id: UUID, user_id: UUID) -> None:
        rating = await self._rating_repo.find_by_id(rating_id)
        if rating is None:
            raise LookupError("Rating not found")
        book = await self._book_repo.find_by_id(rating.owned_book_id)
        if not book:
            raise LookupError("Book not found")
        if book.library_id != library_id:
            raise PermissionError("Book does not belong to this library")
        if rating.user_id != user_id:
            raise PermissionError("Cannot delete another user's rating")
        await self._rating_repo.delete(rating)
        logger.info("Book %s rating %s deleted from library %s", rating.owned_book_id, rating_id, library_id)


class ListBookRatingsUseCase:
    def __init__(self, book_repo: OwnedBookRepository, rating_repo: BookRatingRepository) -> None:
        self._book_repo = book_repo
        self._rating_repo = rating_repo

    async def execute(self, book_id: UUID, library_id: UUID) -> list[BookRating]:
        book = await self._book_repo.find_by_id(book_id)
        if not book:
            raise LookupError("Book not found")
        if book.library_id != library_id:
            raise PermissionError("Book does not belong to this library")
        return await self._rating_repo.list_by_book(book_id)


class GetBookRatingStatsUseCase:
    def __init__(self, book_repo: OwnedBookRepository, rating_repo: BookRatingRepository) -> None:
        self._book_repo = book_repo
        self._rating_repo = rating_repo

    async def execute(self, book_id: UUID, library_id: UUID) -> LibraryRatingStats:
        book = await self._book_repo.find_by_id(book_id)
        if not book:
            raise LookupError("Book not found")
        if book.library_id != library_id:
            raise PermissionError("Book does not belong to this library")
        ratings = await self._rating_repo.list_by_book(book_id)
        return LibraryRatingStats.from_ratings(book_id, ratings)


class ListLibraryRatingsUseCase:
    def __init__(self, rating_repo: BookRatingRepository) -> None:
        self._rating_repo = rating_repo

    async def execute(self, library_id: UUID) -> list[BookRating]:
        return await self._rating_repo.list_by_library(library_id)
