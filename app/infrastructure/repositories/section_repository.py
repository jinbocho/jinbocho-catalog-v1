from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Section
from app.domain.repositories import SectionRepository
from app.infrastructure.models import BookcaseModel, SectionModel


class SQLAlchemySectionRepository(SectionRepository):
	def __init__(self, session: AsyncSession) -> None:
		self._session = session

	@staticmethod
	def _to_entity(model: SectionModel) -> Section:
		return Section(
			id=model.id,
			bookcase_id=model.bookcase_id,
			section_index=model.section_index,
			label=model.label,
			created_at=model.created_at,
			updated_at=model.updated_at,
		)

	async def find_by_id(self, section_id: UUID) -> Section | None:
		model = await self._session.get(SectionModel, section_id)
		return self._to_entity(model) if model else None

	async def find_all_by_bookcase(self, bookcase_id: UUID, limit: int = 50, offset: int = 0) -> list[Section]:
		result = await self._session.execute(
			select(SectionModel)
			.where(SectionModel.bookcase_id == bookcase_id)
			.order_by(SectionModel.section_index)
			.limit(limit)
			.offset(offset)
		)
		return [self._to_entity(model) for model in result.scalars().all()]

	async def find_all_by_family(
		self,
		family_id: UUID,
		bookcase_id: UUID | None = None,
		limit: int = 50,
		offset: int = 0,
	) -> list[Section]:
		query = (
			select(SectionModel)
			.join(BookcaseModel, SectionModel.bookcase_id == BookcaseModel.id)
			.where(BookcaseModel.family_id == family_id)
		)
		if bookcase_id is not None:
			query = query.where(SectionModel.bookcase_id == bookcase_id)
		result = await self._session.execute(
			query.order_by(SectionModel.section_index).limit(limit).offset(offset)
		)
		return [self._to_entity(model) for model in result.scalars().all()]

	async def find_by_index(self, bookcase_id: UUID, section_index: int) -> Section | None:
		result = await self._session.execute(
			select(SectionModel).where(
				SectionModel.bookcase_id == bookcase_id, SectionModel.section_index == section_index
			)
		)
		model = result.scalars().first()
		return self._to_entity(model) if model else None

	async def save(self, section: Section) -> Section:
		model = await self._session.get(SectionModel, section.id)
		if model is None:
			model = SectionModel(
				id=section.id,
				bookcase_id=section.bookcase_id,
				section_index=section.section_index,
				label=section.label,
				created_at=section.created_at,
				updated_at=section.updated_at,
			)
			self._session.add(model)
		else:
			model.bookcase_id = section.bookcase_id
			model.section_index = section.section_index
			model.label = section.label
			model.updated_at = section.updated_at
		await self._session.flush()
		await self._session.refresh(model)
		return self._to_entity(model)

	async def delete(self, section_id: UUID) -> None:
		model = await self._session.get(SectionModel, section_id)
		if model is not None:
			await self._session.delete(model)
			await self._session.flush()
