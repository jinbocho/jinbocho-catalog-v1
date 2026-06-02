from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import BibliographicRecord
from app.domain.repositories import BibliographicRecordRepository
from app.infrastructure.models import BibliographicRecordModel


class SQLAlchemyBibliographicRecordRepository(BibliographicRecordRepository):
	def __init__(self, session: AsyncSession) -> None:
		self._session = session

	@staticmethod
	def _to_entity(model: BibliographicRecordModel) -> BibliographicRecord:
		return BibliographicRecord(
			id=model.id,
			family_id=model.family_id,
			title=model.title,
			main_author=model.main_author,
			other_authors=list(model.other_authors) if model.other_authors else [],
			isbn=model.isbn,
			publisher=model.publisher,
			publication_year=model.publication_year,
			language=model.language,
			genre=model.genre,
			cover_url=model.cover_url,
			notes=model.notes,
			created_at=model.created_at,
			updated_at=model.updated_at,
		)

	async def find_by_id(self, record_id: UUID) -> BibliographicRecord | None:
		model = await self._session.get(BibliographicRecordModel, record_id)
		return self._to_entity(model) if model else None

	async def find_by_isbn(self, family_id: UUID, isbn: str) -> BibliographicRecord | None:
		result = await self._session.execute(
			select(BibliographicRecordModel).where(
				BibliographicRecordModel.family_id == family_id,
				BibliographicRecordModel.isbn == isbn,
			)
		)
		model = result.scalar_one_or_none()
		return self._to_entity(model) if model else None

	async def find_all_by_family(
		self,
		family_id: UUID,
		q: str | None = None,
		limit: int = 50,
		offset: int = 0,
	) -> list[BibliographicRecord]:
		query = select(BibliographicRecordModel).where(BibliographicRecordModel.family_id == family_id)
		if q:
			ts_vector = func.to_tsvector(
				"simple",
				func.concat(
					func.coalesce(BibliographicRecordModel.title, ""),
					" ",
					func.coalesce(BibliographicRecordModel.main_author, ""),
					" ",
					func.coalesce(BibliographicRecordModel.isbn, ""),
				),
			)
			query = query.where(ts_vector.op("@@")(func.plainto_tsquery("simple", q)))
		result = await self._session.execute(query.order_by(BibliographicRecordModel.created_at.desc()).limit(limit).offset(offset))
		return [self._to_entity(model) for model in result.scalars().all()]

	async def find_all_by_ids(self, record_ids: list[UUID]) -> list[BibliographicRecord]:
		if not record_ids:
			return []
		result = await self._session.execute(
			select(BibliographicRecordModel).where(BibliographicRecordModel.id.in_(record_ids))
		)
		return [self._to_entity(model) for model in result.scalars().all()]

	async def save(self, record: BibliographicRecord) -> BibliographicRecord:
		model = await self._session.get(BibliographicRecordModel, record.id)
		if model is None:
			model = BibliographicRecordModel(
				id=record.id,
				family_id=record.family_id,
				title=record.title,
				main_author=record.main_author,
				other_authors=record.other_authors or None,
				isbn=record.isbn,
				publisher=record.publisher,
				publication_year=record.publication_year,
				language=record.language,
				genre=record.genre,
				cover_url=record.cover_url,
				notes=record.notes,
				created_at=record.created_at,
				updated_at=record.updated_at,
			)
			self._session.add(model)
		else:
			model.title = record.title
			model.main_author = record.main_author
			model.other_authors = record.other_authors or None
			model.isbn = record.isbn
			model.publisher = record.publisher
			model.publication_year = record.publication_year
			model.language = record.language
			model.genre = record.genre
			model.cover_url = record.cover_url
			model.notes = record.notes
			model.updated_at = record.updated_at
		await self._session.flush()
		await self._session.refresh(model)
		return self._to_entity(model)

	async def delete(self, record_id: UUID) -> None:
		model = await self._session.get(BibliographicRecordModel, record_id)
		if model is not None:
			await self._session.delete(model)
			await self._session.flush()
