from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import BookRating
from app.domain.repositories import BookRatingRepository
from app.infrastructure.models.book_rating_model import BookRatingModel
from app.infrastructure.models.owned_book_model import OwnedBookModel


class SQLAlchemyBookRatingRepository(BookRatingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: BookRatingModel) -> BookRating:
        return BookRating(
            id=model.id,
            owned_book_id=model.owned_book_id,
            user_id=model.user_id,
            rating=model.rating,
            review=model.review,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def add(self, rating: BookRating) -> BookRating:
        model = BookRatingModel(
            id=rating.id,
            owned_book_id=rating.owned_book_id,
            user_id=rating.user_id,
            rating=rating.rating,
            review=rating.review,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def save(self, rating: BookRating) -> BookRating:
        model = await self._session.get(BookRatingModel, rating.id)
        if model is None:
            raise LookupError(f"BookRating {rating.id} not found")
        model.rating = rating.rating
        model.review = rating.review
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def find_by_id(self, rating_id: UUID) -> BookRating | None:
        model = await self._session.get(BookRatingModel, rating_id)
        return self._to_entity(model) if model else None

    async def find_by_book_and_user(self, owned_book_id: UUID, user_id: UUID) -> BookRating | None:
        result = await self._session.execute(
            select(BookRatingModel).where(
                BookRatingModel.owned_book_id == owned_book_id,
                BookRatingModel.user_id == user_id,
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_book(self, owned_book_id: UUID) -> list[BookRating]:
        result = await self._session.execute(
            select(BookRatingModel).where(BookRatingModel.owned_book_id == owned_book_id)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_library(self, library_id: UUID) -> list[BookRating]:
        result = await self._session.execute(
            select(BookRatingModel)
            .join(OwnedBookModel, BookRatingModel.owned_book_id == OwnedBookModel.id)
            .where(OwnedBookModel.library_id == library_id)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def delete(self, rating: BookRating) -> None:
        model = await self._session.get(BookRatingModel, rating.id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

    async def restore(self, rating: BookRating) -> BookRating:
        model = await self._session.get(BookRatingModel, rating.id)
        if model is None:
            existing_result = await self._session.execute(
                select(BookRatingModel).where(
                    BookRatingModel.owned_book_id == rating.owned_book_id,
                    BookRatingModel.user_id == rating.user_id,
                )
            )
            model = existing_result.scalar_one_or_none()
        if model is None:
            model = BookRatingModel(
                id=rating.id,
                owned_book_id=rating.owned_book_id,
                user_id=rating.user_id,
                rating=rating.rating,
                review=rating.review,
            )
            self._session.add(model)
        else:
            model.rating = rating.rating
            model.review = rating.review
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)
