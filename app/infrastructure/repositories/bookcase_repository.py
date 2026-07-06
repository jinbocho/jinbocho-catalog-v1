from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Bookcase
from app.domain.repositories import BookcaseRepository
from app.infrastructure.models import BookcaseModel


class SQLAlchemyBookcaseRepository(BookcaseRepository):
	def __init__(self, session: AsyncSession) -> None:
		self._session = session

	@staticmethod
	def _to_entity(model: BookcaseModel) -> Bookcase:
		return Bookcase(
			id=model.id,
			library_id=model.library_id,
			room_id=model.room_id,
			name=model.name,
			description=model.description,
			type=model.type,
			notes=model.notes,
			image_url=model.image_url,
			created_at=model.created_at,
			updated_at=model.updated_at,
		)

	async def find_by_id(self, bookcase_id: UUID) -> Bookcase | None:
		model = await self._session.get(BookcaseModel, bookcase_id)
		return self._to_entity(model) if model else None

	async def find_all_by_library(
		self,
		library_id: UUID,
		room_id: UUID | None = None,
		limit: int = 50,
		offset: int = 0,
	) -> list[Bookcase]:
		query = select(BookcaseModel).where(BookcaseModel.library_id == library_id)
		if room_id is not None:
			query = query.where(BookcaseModel.room_id == room_id)
		result = await self._session.execute(query.order_by(BookcaseModel.name).limit(limit).offset(offset))
		return [self._to_entity(model) for model in result.scalars().all()]

	async def find_by_name(self, room_id: UUID, name: str) -> Bookcase | None:
		result = await self._session.execute(
			select(BookcaseModel).where(BookcaseModel.room_id == room_id, BookcaseModel.name == name)
		)
		model = result.scalars().first()
		return self._to_entity(model) if model else None

	async def save(self, bookcase: Bookcase) -> Bookcase:
		model = await self._session.get(BookcaseModel, bookcase.id)
		if model is None:
			model = BookcaseModel(
				id=bookcase.id,
				library_id=bookcase.library_id,
				room_id=bookcase.room_id,
				name=bookcase.name,
				description=bookcase.description,
				type=bookcase.type,
				notes=bookcase.notes,
				image_url=bookcase.image_url,
				created_at=bookcase.created_at,
				updated_at=bookcase.updated_at,
			)
			self._session.add(model)
		else:
			model.room_id = bookcase.room_id
			model.name = bookcase.name
			model.description = bookcase.description
			model.type = bookcase.type
			model.notes = bookcase.notes
			model.image_url = bookcase.image_url
			model.updated_at = bookcase.updated_at
		await self._session.flush()
		await self._session.refresh(model)
		return self._to_entity(model)

	async def delete(self, bookcase_id: UUID) -> None:
		model = await self._session.get(BookcaseModel, bookcase_id)
		if model is not None:
			await self._session.delete(model)
			await self._session.flush()

	async def delete_all_by_library(self, library_id: UUID) -> None:
		await self._session.execute(sa_delete(BookcaseModel).where(BookcaseModel.library_id == library_id))
		await self._session.flush()
