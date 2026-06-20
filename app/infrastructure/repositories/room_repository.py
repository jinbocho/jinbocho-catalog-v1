from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Room
from app.domain.repositories import RoomRepository
from app.infrastructure.models import RoomModel


class SQLAlchemyRoomRepository(RoomRepository):
	def __init__(self, session: AsyncSession) -> None:
		self._session = session

	@staticmethod
	def _to_entity(model: RoomModel) -> Room:
		return Room(
			id=model.id,
			family_id=model.family_id,
			name=model.name,
			description=model.description,
			created_at=model.created_at,
			updated_at=model.updated_at,
		)

	async def find_by_id(self, room_id: UUID) -> Room | None:
		model = await self._session.get(RoomModel, room_id)
		return self._to_entity(model) if model else None

	async def find_all_by_family(self, family_id: UUID, limit: int = 50, offset: int = 0) -> list[Room]:
		result = await self._session.execute(
			select(RoomModel).where(RoomModel.family_id == family_id).order_by(RoomModel.name).limit(limit).offset(offset)
		)
		return [self._to_entity(model) for model in result.scalars().all()]

	async def find_by_name(self, family_id: UUID, name: str) -> Room | None:
		result = await self._session.execute(
			select(RoomModel).where(RoomModel.family_id == family_id, RoomModel.name == name)
		)
		model = result.scalars().first()
		return self._to_entity(model) if model else None

	async def save(self, room: Room) -> Room:
		model = await self._session.get(RoomModel, room.id)
		if model is None:
			model = RoomModel(
				id=room.id,
				family_id=room.family_id,
				name=room.name,
				description=room.description,
				created_at=room.created_at,
				updated_at=room.updated_at,
			)
			self._session.add(model)
		else:
			model.name = room.name
			model.description = room.description
			model.updated_at = room.updated_at
		await self._session.flush()
		await self._session.refresh(model)
		return self._to_entity(model)

	async def delete(self, room_id: UUID) -> None:
		model = await self._session.get(RoomModel, room_id)
		if model is not None:
			await self._session.delete(model)
			await self._session.flush()

	async def delete_all_by_family(self, family_id: UUID) -> None:
		await self._session.execute(sa_delete(RoomModel).where(RoomModel.family_id == family_id))
		await self._session.flush()
