from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import WishlistItem
from app.domain.repositories import WishlistRepository
from app.infrastructure.models.wishlist_item_model import WishlistItemModel


class SQLAlchemyWishlistRepository(WishlistRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: WishlistItemModel) -> WishlistItem:
        return WishlistItem(
            id=model.id,
            library_id=model.library_id,
            user_id=model.user_id,
            bibliographic_record_id=model.bibliographic_record_id,
            added_at=model.added_at,
            notes=model.notes,
            priority=model.priority,
        )

    async def get(self, item_id: UUID, library_id: UUID) -> WishlistItem | None:
        result = await self._session.execute(
            select(WishlistItemModel).where(
                WishlistItemModel.id == item_id,
                WishlistItemModel.library_id == library_id,
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_library(self, library_id: UUID) -> list[WishlistItem]:
        result = await self._session.execute(
            select(WishlistItemModel)
            .where(WishlistItemModel.library_id == library_id)
            .order_by(
                WishlistItemModel.priority.asc().nulls_last(),
                WishlistItemModel.added_at.desc(),
            )
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_user(self, user_id: UUID) -> list[WishlistItem]:
        result = await self._session.execute(
            select(WishlistItemModel)
            .where(WishlistItemModel.user_id == user_id)
            .order_by(
                WishlistItemModel.priority.asc().nulls_last(),
                WishlistItemModel.added_at.desc(),
            )
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def add(self, item: WishlistItem) -> WishlistItem:
        model = WishlistItemModel(
            id=item.id,
            library_id=item.library_id,
            user_id=item.user_id,
            bibliographic_record_id=item.bibliographic_record_id,
            notes=item.notes,
            priority=item.priority,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def delete(self, item_id: UUID, library_id: UUID) -> None:
        result = await self._session.execute(
            select(WishlistItemModel).where(
                WishlistItemModel.id == item_id,
                WishlistItemModel.library_id == library_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

    async def exists_for_user_and_record(self, user_id: UUID, record_id: UUID) -> bool:
        result = await self._session.execute(
            select(WishlistItemModel.id).where(
                WishlistItemModel.user_id == user_id,
                WishlistItemModel.bibliographic_record_id == record_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def restore(self, item: WishlistItem) -> WishlistItem:
        model = await self._session.get(WishlistItemModel, item.id)
        if model is None:
            existing = await self._session.execute(
                select(WishlistItemModel).where(
                    WishlistItemModel.user_id == item.user_id,
                    WishlistItemModel.bibliographic_record_id == item.bibliographic_record_id,
                )
            )
            model = existing.scalars().first()
        if model is None:
            model = WishlistItemModel(
                id=item.id,
                library_id=item.library_id,
                user_id=item.user_id,
                bibliographic_record_id=item.bibliographic_record_id,
                added_at=item.added_at,
                notes=item.notes,
                priority=item.priority,
            )
            self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)
