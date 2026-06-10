from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import BookRead
from app.domain.repositories import BookReadRepository
from app.infrastructure.models.book_read_model import BookReadModel
from app.infrastructure.models.owned_book_model import OwnedBookModel


class SQLAlchemyBookReadRepository(BookReadRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: BookReadModel) -> BookRead:
        return BookRead(
            id=model.id,
            owned_book_id=model.owned_book_id,
            user_id=model.user_id,
            read_at=model.read_at,
        )

    async def add(self, owned_book_id: UUID, user_id: UUID) -> BookRead:
        result = await self._session.execute(
            select(BookReadModel).where(
                BookReadModel.owned_book_id == owned_book_id,
                BookReadModel.user_id == user_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return self._to_entity(existing)
        model = BookReadModel(owned_book_id=owned_book_id, user_id=user_id)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def remove(self, owned_book_id: UUID, user_id: UUID) -> None:
        result = await self._session.execute(
            select(BookReadModel).where(
                BookReadModel.owned_book_id == owned_book_id,
                BookReadModel.user_id == user_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

    async def list_by_book(self, owned_book_id: UUID) -> list[BookRead]:
        result = await self._session.execute(
            select(BookReadModel).where(BookReadModel.owned_book_id == owned_book_id)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_family(self, family_id: UUID) -> list[BookRead]:
        result = await self._session.execute(
            select(BookReadModel)
            .join(OwnedBookModel, BookReadModel.owned_book_id == OwnedBookModel.id)
            .where(OwnedBookModel.family_id == family_id)
        )
        return [self._to_entity(m) for m in result.scalars().all()]
