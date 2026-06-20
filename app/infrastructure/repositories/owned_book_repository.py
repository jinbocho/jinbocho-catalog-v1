from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import OwnedBook
from app.domain.repositories import OwnedBookRepository
from app.infrastructure.models import OwnedBookModel


class SQLAlchemyOwnedBookRepository(OwnedBookRepository):
	def __init__(self, session: AsyncSession) -> None:
		self._session = session

	@staticmethod
	def _to_entity(model: OwnedBookModel) -> OwnedBook:
		return OwnedBook(
			id=model.id,
			family_id=model.family_id,
			bibliographic_record_id=model.bibliographic_record_id,
			room_id=model.room_id,
			bookcase_id=model.bookcase_id,
			section_id=model.section_id,
			shelf_id=model.shelf_id,
			shelf_position=model.shelf_position,
			position_description=model.position_description,
			condition=model.condition,
			purchase_date=model.purchase_date,
			purchase_price=Decimal(model.purchase_price) if model.purchase_price is not None else None,
			source=model.source,
			reading_status=model.reading_status,
			current_reader_id=model.current_reader_id,
			owner_id=model.owner_id,
			tags=list(model.tags) if model.tags else [],
			notes=model.notes,
			is_intentional_duplicate=model.is_intentional_duplicate,
			duplicate_notes=model.duplicate_notes,
			created_at=model.created_at,
			updated_at=model.updated_at,
		)

	async def find_by_id(self, book_id: UUID) -> OwnedBook | None:
		model = await self._session.get(OwnedBookModel, book_id)
		return self._to_entity(model) if model else None

	async def find_all_by_family(
		self,
		family_id: UUID,
		shelf_id: UUID | None = None,
		reading_status: str | None = None,
		tag: str | None = None,
		limit: int = 50,
		offset: int = 0,
	) -> list[OwnedBook]:
		query = select(OwnedBookModel).where(OwnedBookModel.family_id == family_id)
		if shelf_id is not None:
			query = query.where(OwnedBookModel.shelf_id == shelf_id)
		if reading_status is not None:
			query = query.where(OwnedBookModel.reading_status == reading_status)
		if tag is not None:
			query = query.where(OwnedBookModel.tags.contains([tag]))
		result = await self._session.execute(query.order_by(OwnedBookModel.created_at.desc()).limit(limit).offset(offset))
		return [self._to_entity(model) for model in result.scalars().all()]

	async def find_all_by_shelf_ids(self, shelf_ids: list[UUID]) -> list[OwnedBook]:
		if not shelf_ids:
			return []
		result = await self._session.execute(
			select(OwnedBookModel)
			.where(OwnedBookModel.shelf_id.in_(shelf_ids))
			.order_by(OwnedBookModel.shelf_id, OwnedBookModel.shelf_position, OwnedBookModel.created_at.desc())
		)
		return [self._to_entity(model) for model in result.scalars().all()]

	async def exists_by_bibliographic_record_id(self, record_id: UUID) -> bool:
		result = await self._session.execute(
			select(func.count()).select_from(OwnedBookModel).where(OwnedBookModel.bibliographic_record_id == record_id)
		)
		return bool(result.scalar_one())

	async def find_duplicate(
		self,
		family_id: UUID,
		bibliographic_record_id: UUID,
		room_id: UUID | None,
		bookcase_id: UUID | None,
		section_id: UUID | None,
		shelf_id: UUID | None,
		shelf_position: int | None,
	) -> OwnedBook | None:
		def _eq(column: Any, value: Any) -> Any:
			return column.is_(None) if value is None else column == value

		result = await self._session.execute(
			select(OwnedBookModel).where(
				OwnedBookModel.family_id == family_id,
				OwnedBookModel.bibliographic_record_id == bibliographic_record_id,
				_eq(OwnedBookModel.room_id, room_id),
				_eq(OwnedBookModel.bookcase_id, bookcase_id),
				_eq(OwnedBookModel.section_id, section_id),
				_eq(OwnedBookModel.shelf_id, shelf_id),
				_eq(OwnedBookModel.shelf_position, shelf_position),
			)
		)
		model = result.scalars().first()
		return self._to_entity(model) if model else None

	async def save(self, owned_book: OwnedBook) -> OwnedBook:
		model = await self._session.get(OwnedBookModel, owned_book.id)
		if model is None:
			model = OwnedBookModel(
				id=owned_book.id,
				family_id=owned_book.family_id,
				bibliographic_record_id=owned_book.bibliographic_record_id,
				room_id=owned_book.room_id,
				bookcase_id=owned_book.bookcase_id,
				section_id=owned_book.section_id,
				shelf_id=owned_book.shelf_id,
				shelf_position=owned_book.shelf_position,
				position_description=owned_book.position_description,
				condition=owned_book.condition,
				purchase_date=owned_book.purchase_date,
				purchase_price=owned_book.purchase_price,
				source=owned_book.source,
				reading_status=owned_book.reading_status,
				current_reader_id=owned_book.current_reader_id,
				owner_id=owned_book.owner_id,
				tags=owned_book.tags or None,
				notes=owned_book.notes,
				is_intentional_duplicate=owned_book.is_intentional_duplicate,
				duplicate_notes=owned_book.duplicate_notes,
				created_at=owned_book.created_at,
				updated_at=owned_book.updated_at,
			)
			self._session.add(model)
		else:
			model.bibliographic_record_id = owned_book.bibliographic_record_id
			model.room_id = owned_book.room_id
			model.bookcase_id = owned_book.bookcase_id
			model.section_id = owned_book.section_id
			model.shelf_id = owned_book.shelf_id
			model.shelf_position = owned_book.shelf_position
			model.position_description = owned_book.position_description
			model.condition = owned_book.condition
			model.purchase_date = owned_book.purchase_date
			model.purchase_price = owned_book.purchase_price
			model.source = owned_book.source
			model.reading_status = owned_book.reading_status
			model.current_reader_id = owned_book.current_reader_id
			model.owner_id = owned_book.owner_id
			model.tags = owned_book.tags or None
			model.notes = owned_book.notes
			model.is_intentional_duplicate = owned_book.is_intentional_duplicate
			model.duplicate_notes = owned_book.duplicate_notes
			model.updated_at = owned_book.updated_at
		await self._session.flush()
		await self._session.refresh(model)
		return self._to_entity(model)

	async def delete(self, book_id: UUID) -> None:
		model = await self._session.get(OwnedBookModel, book_id)
		if model is not None:
			await self._session.delete(model)
			await self._session.flush()
