from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import BookAbandonment
from app.domain.repositories import BookAbandonmentRepository
from app.infrastructure.models.book_abandonment_model import BookAbandonmentModel


class SQLAlchemyBookAbandonmentRepository(BookAbandonmentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: BookAbandonmentModel) -> BookAbandonment:
        return BookAbandonment(
            id=model.id,
            owned_book_id=model.owned_book_id,
            user_id=model.user_id,
            abandoned_at=model.abandoned_at,
        )

    async def add(self, owned_book_id: UUID, user_id: UUID, abandoned_at: datetime | None = None) -> BookAbandonment:
        result = await self._session.execute(
            select(BookAbandonmentModel).where(
                BookAbandonmentModel.owned_book_id == owned_book_id,
                BookAbandonmentModel.user_id == user_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            if abandoned_at is not None:
                existing.abandoned_at = abandoned_at
                await self._session.flush()
                await self._session.refresh(existing)
            return self._to_entity(existing)
        model = BookAbandonmentModel(owned_book_id=owned_book_id, user_id=user_id)
        if abandoned_at is not None:
            model.abandoned_at = abandoned_at
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def remove(self, owned_book_id: UUID, user_id: UUID) -> None:
        result = await self._session.execute(
            select(BookAbandonmentModel).where(
                BookAbandonmentModel.owned_book_id == owned_book_id,
                BookAbandonmentModel.user_id == user_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

    async def is_abandoned(self, owned_book_id: UUID, user_id: UUID) -> bool:
        result = await self._session.execute(
            select(BookAbandonmentModel.id).where(
                BookAbandonmentModel.owned_book_id == owned_book_id,
                BookAbandonmentModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def list_abandoned_book_ids(self, owned_book_ids: list[UUID], user_id: UUID) -> set[UUID]:
        if not owned_book_ids:
            return set()
        result = await self._session.execute(
            select(BookAbandonmentModel.owned_book_id).where(
                BookAbandonmentModel.user_id == user_id,
                BookAbandonmentModel.owned_book_id.in_(owned_book_ids),
            )
        )
        return set(result.scalars().all())
