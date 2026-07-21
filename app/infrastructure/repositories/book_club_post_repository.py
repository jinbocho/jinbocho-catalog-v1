from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import BookClubPost
from app.domain.repositories import BookClubPostRepository
from app.infrastructure.models.book_club_post_model import BookClubPostModel


class SQLAlchemyBookClubPostRepository(BookClubPostRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: BookClubPostModel) -> BookClubPost:
        return BookClubPost(
            id=model.id,
            cycle_id=model.cycle_id,
            user_id=model.user_id,
            body=model.body,
            parent_post_id=model.parent_post_id,
            is_spoiler=model.is_spoiler,
            created_at=model.created_at,
        )

    async def add(self, post: BookClubPost) -> BookClubPost:
        model = BookClubPostModel(
            id=post.id,
            cycle_id=post.cycle_id,
            user_id=post.user_id,
            body=post.body,
            parent_post_id=post.parent_post_id,
            is_spoiler=post.is_spoiler,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def find_by_id(self, post_id: UUID) -> BookClubPost | None:
        model = await self._session.get(BookClubPostModel, post_id)
        return self._to_entity(model) if model else None

    async def list_by_cycle(self, cycle_id: UUID) -> list[BookClubPost]:
        result = await self._session.execute(
            select(BookClubPostModel)
            .where(BookClubPostModel.cycle_id == cycle_id)
            .order_by(BookClubPostModel.created_at.asc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def delete(self, post: BookClubPost) -> None:
        model = await self._session.get(BookClubPostModel, post.id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()
