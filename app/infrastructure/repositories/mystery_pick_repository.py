from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import MysteryPick, MysteryPickStatus
from app.domain.repositories import MysteryPickRepository
from app.infrastructure.models.mystery_pick_model import MysteryPickModel


class SQLAlchemyMysteryPickRepository(MysteryPickRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: MysteryPickModel) -> MysteryPick:
        return MysteryPick(
            id=model.id,
            library_id=model.library_id,
            owned_book_id=model.owned_book_id,
            child_user_id=model.child_user_id,
            hint_text=model.hint_text,
            status=MysteryPickStatus(model.status),
            created_by=model.created_by,
            created_at=model.created_at,
        )

    async def add(self, pick: MysteryPick) -> MysteryPick:
        model = MysteryPickModel(
            id=pick.id,
            library_id=pick.library_id,
            owned_book_id=pick.owned_book_id,
            child_user_id=pick.child_user_id,
            hint_text=pick.hint_text,
            status=pick.status.value,
            created_by=pick.created_by,
            created_at=pick.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def find_by_id(self, pick_id: UUID) -> MysteryPick | None:
        result = await self._session.execute(select(MysteryPickModel).where(MysteryPickModel.id == pick_id))
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, pick: MysteryPick) -> MysteryPick:
        model = await self._session.get(MysteryPickModel, pick.id)
        if model is None:
            return await self.add(pick)
        model.status = pick.status.value
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def list_by_child(self, child_user_id: UUID, library_id: UUID) -> list[MysteryPick]:
        result = await self._session.execute(
            select(MysteryPickModel)
            .where(MysteryPickModel.child_user_id == child_user_id, MysteryPickModel.library_id == library_id)
            .order_by(MysteryPickModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]
