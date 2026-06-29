from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.domain.entities import BookRating, FamilyRatingStats
from app.domain.repositories import BookRatingRepository, OwnedBookRepository


@dataclass
class CreateBookRatingInput:
    book_id: UUID
    family_id: UUID
    user_id: UUID
    rating: int
    review: str | None = None


@dataclass
class UpdateBookRatingInput:
    rating_id: UUID
    book_id: UUID
    family_id: UUID
    user_id: UUID
    rating: int | None = None
    review: str | None = None


class CreateBookRatingUseCase:
    def __init__(self, book_repo: OwnedBookRepository, rating_repo: BookRatingRepository) -> None:
        self._book_repo = book_repo
        self._rating_repo = rating_repo

    async def execute(self, inp: CreateBookRatingInput) -> BookRating:
        book = await self._book_repo.find_by_id(inp.book_id)
        if not book or book.family_id != inp.family_id:
            raise LookupError("Book not found")
        existing = await self._rating_repo.find_by_book_and_user(inp.book_id, inp.user_id)
        if existing is not None:
            raise ValueError("You have already rated this book")
        return await self._rating_repo.add(
            BookRating(
                owned_book_id=inp.book_id,
                user_id=inp.user_id,
                rating=inp.rating,
                review=inp.review,
            )
        )


class UpdateBookRatingUseCase:
    def __init__(self, book_repo: OwnedBookRepository, rating_repo: BookRatingRepository) -> None:
        self._book_repo = book_repo
        self._rating_repo = rating_repo

    async def execute(self, inp: UpdateBookRatingInput) -> BookRating:
        rating = await self._rating_repo.find_by_id(inp.rating_id)
        if rating is None:
            raise LookupError("Rating not found")
        book = await self._book_repo.find_by_id(inp.book_id)
        if not book or book.family_id != inp.family_id:
            raise LookupError("Book not found")
        if rating.user_id != inp.user_id:
            raise PermissionError("Cannot modify another user's rating")
        if inp.rating is not None:
            rating.rating = inp.rating
            if not 1 <= rating.rating <= 5:
                raise ValueError("rating must be between 1 and 5")
        if inp.review is not None:
            rating.review = inp.review
        rating.updated_at = datetime.now(UTC)
        return await self._rating_repo.save(rating)


class DeleteBookRatingUseCase:
    def __init__(self, book_repo: OwnedBookRepository, rating_repo: BookRatingRepository) -> None:
        self._book_repo = book_repo
        self._rating_repo = rating_repo

    async def execute(self, rating_id: UUID, family_id: UUID, user_id: UUID) -> None:
        rating = await self._rating_repo.find_by_id(rating_id)
        if rating is None:
            raise LookupError("Rating not found")
        book = await self._book_repo.find_by_id(rating.owned_book_id)
        if not book or book.family_id != family_id:
            raise LookupError("Book not found")
        if rating.user_id != user_id:
            raise PermissionError("Cannot delete another user's rating")
        await self._rating_repo.delete(rating)


class ListBookRatingsUseCase:
    def __init__(self, book_repo: OwnedBookRepository, rating_repo: BookRatingRepository) -> None:
        self._book_repo = book_repo
        self._rating_repo = rating_repo

    async def execute(self, book_id: UUID, family_id: UUID) -> list[BookRating]:
        book = await self._book_repo.find_by_id(book_id)
        if not book or book.family_id != family_id:
            raise LookupError("Book not found")
        return await self._rating_repo.list_by_book(book_id)


class GetBookRatingStatsUseCase:
    def __init__(self, book_repo: OwnedBookRepository, rating_repo: BookRatingRepository) -> None:
        self._book_repo = book_repo
        self._rating_repo = rating_repo

    async def execute(self, book_id: UUID, family_id: UUID) -> FamilyRatingStats:
        book = await self._book_repo.find_by_id(book_id)
        if not book or book.family_id != family_id:
            raise LookupError("Book not found")
        ratings = await self._rating_repo.list_by_book(book_id)
        return FamilyRatingStats.from_ratings(book_id, ratings)


class ListFamilyRatingsUseCase:
    def __init__(self, rating_repo: BookRatingRepository) -> None:
        self._rating_repo = rating_repo

    async def execute(self, family_id: UUID) -> list[BookRating]:
        return await self._rating_repo.list_by_family(family_id)
