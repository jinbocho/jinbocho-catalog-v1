from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import BookHistory
from app.domain.repositories import BookHistoryRepository
from app.infrastructure.models import BookHistoryModel
from app.infrastructure.models.owned_book_model import OwnedBookModel


class SQLAlchemyBookHistoryRepository(BookHistoryRepository):
	def __init__(self, session: AsyncSession) -> None:
		self._session = session

	@staticmethod
	def _to_entity(model: BookHistoryModel) -> BookHistory:
		return BookHistory(
			id=model.id,
			owned_book_id=model.owned_book_id,
			event_type=model.event_type,
			changed_by=model.changed_by,
			old_data=model.old_data,
			new_data=model.new_data,
			created_at=model.created_at,
		)

	async def find_by_book(self, book_id: UUID, limit: int = 50, offset: int = 0) -> list[BookHistory]:
		result = await self._session.execute(
			select(BookHistoryModel)
			.where(BookHistoryModel.owned_book_id == book_id)
			.order_by(BookHistoryModel.created_at.desc())
			.limit(limit)
			.offset(offset)
		)
		return [self._to_entity(model) for model in result.scalars().all()]

	async def save(self, history: BookHistory) -> BookHistory:
		model = BookHistoryModel(
			id=history.id,
			owned_book_id=history.owned_book_id,
			event_type=history.event_type,
			changed_by=history.changed_by,
			old_data=history.old_data,
			new_data=history.new_data,
			created_at=history.created_at,
		)
		self._session.add(model)
		await self._session.flush()
		await self._session.refresh(model)
		return self._to_entity(model)

	async def find_all_by_family(self, family_id: UUID) -> list[BookHistory]:
		result = await self._session.execute(
			select(BookHistoryModel)
			.join(OwnedBookModel, BookHistoryModel.owned_book_id == OwnedBookModel.id)
			.where(OwnedBookModel.family_id == family_id)
			.order_by(BookHistoryModel.created_at.desc())
		)
		return [self._to_entity(model) for model in result.scalars().all()]

	async def restore(self, history: BookHistory) -> BookHistory:
		model = await self._session.get(BookHistoryModel, history.id)
		if model is None:
			# No id collision is possible (import always mints a fresh one) —
			# but the same audit entry might already have been restored by a
			# previous import of this same backup.
			existing = await self._session.execute(
				select(BookHistoryModel).where(
					BookHistoryModel.owned_book_id == history.owned_book_id,
					BookHistoryModel.event_type == history.event_type,
					BookHistoryModel.changed_by == history.changed_by,
					BookHistoryModel.created_at == history.created_at,
				)
			)
			model = existing.scalars().first()
		if model is None:
			model = BookHistoryModel(
				id=history.id,
				owned_book_id=history.owned_book_id,
				event_type=history.event_type,
				changed_by=history.changed_by,
				old_data=history.old_data,
				new_data=history.new_data,
				created_at=history.created_at,
			)
			self._session.add(model)
		await self._session.flush()
		await self._session.refresh(model)
		return self._to_entity(model)
