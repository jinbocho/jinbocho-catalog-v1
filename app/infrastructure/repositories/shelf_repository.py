from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Shelf
from app.domain.repositories import ShelfRepository
from app.infrastructure.models import BookcaseModel, SectionModel, ShelfModel



class SQLAlchemyShelfRepository(ShelfRepository):
	def __init__(self, session: AsyncSession) -> None:
		self._session = session

	@staticmethod
	def _to_entity(model: ShelfModel) -> Shelf:
		return Shelf(
			id=model.id,
			section_id=model.section_id,
			shelf_index=model.shelf_index,
			notes=model.notes,
			created_at=model.created_at,
			updated_at=model.updated_at,
		)

	async def find_by_id(self, shelf_id: UUID) -> Shelf | None:
		model = await self._session.get(ShelfModel, shelf_id)
		return self._to_entity(model) if model else None

	async def find_all_by_section(self, section_id: UUID, limit: int = 50, offset: int = 0) -> list[Shelf]:
		result = await self._session.execute(
			select(ShelfModel).where(ShelfModel.section_id == section_id).order_by(ShelfModel.shelf_index).limit(limit).offset(offset)
		)
		return [self._to_entity(model) for model in result.scalars().all()]

	async def find_all_by_family(
		self,
		family_id: UUID,
		section_id: UUID | None = None,
		limit: int = 50,
		offset: int = 0,
	) -> list[Shelf]:
		query = (
			select(ShelfModel)
			.join(SectionModel, ShelfModel.section_id == SectionModel.id)
			.join(BookcaseModel, SectionModel.bookcase_id == BookcaseModel.id)
			.where(BookcaseModel.family_id == family_id)
		)
		if section_id is not None:
			query = query.where(ShelfModel.section_id == section_id)
		result = await self._session.execute(query.order_by(ShelfModel.shelf_index).limit(limit).offset(offset))
		return [self._to_entity(model) for model in result.scalars().all()]

	async def find_all_by_section_ids(self, section_ids: list[UUID]) -> list[Shelf]:
		if not section_ids:
			return []
		result = await self._session.execute(
			select(ShelfModel)
			.where(ShelfModel.section_id.in_(section_ids))
			.order_by(ShelfModel.section_id, ShelfModel.shelf_index)
		)
		return [self._to_entity(model) for model in result.scalars().all()]

	async def find_by_index(self, section_id: UUID, shelf_index: int) -> Shelf | None:
		result = await self._session.execute(
			select(ShelfModel).where(ShelfModel.section_id == section_id, ShelfModel.shelf_index == shelf_index)
		)
		model = result.scalars().first()
		return self._to_entity(model) if model else None

	async def save(self, shelf: Shelf) -> Shelf:
		model = await self._session.get(ShelfModel, shelf.id)
		if model is None:
			model = ShelfModel(
				id=shelf.id,
				section_id=shelf.section_id,
				shelf_index=shelf.shelf_index,
				notes=shelf.notes,
				created_at=shelf.created_at,
				updated_at=shelf.updated_at,
			)
			self._session.add(model)
		else:
			model.section_id = shelf.section_id
			model.shelf_index = shelf.shelf_index
			model.notes = shelf.notes
			model.updated_at = shelf.updated_at
		await self._session.flush()
		await self._session.refresh(model)
		return self._to_entity(model)

	async def delete(self, shelf_id: UUID) -> None:
		model = await self._session.get(ShelfModel, shelf_id)
		if model is not None:
			await self._session.delete(model)
			await self._session.flush()
