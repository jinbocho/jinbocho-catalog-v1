from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import IsbnLookupCache
from app.domain.repositories import IsbnLookupCacheRepository
from app.infrastructure.models import IsbnLookupCacheModel


class SQLAlchemyIsbnLookupCacheRepository(IsbnLookupCacheRepository):
	def __init__(self, session: AsyncSession) -> None:
		self._session = session

	@staticmethod
	def _to_entity(model: IsbnLookupCacheModel) -> IsbnLookupCache:
		return IsbnLookupCache(
			id=model.id,
			isbn=model.isbn,
			metadata=model.cache_metadata,
			source=model.source,
			fetched_at=model.fetched_at,
			created_at=model.created_at,
		)

	async def find_by_isbn(self, isbn: str) -> IsbnLookupCache | None:
		result = await self._session.execute(select(IsbnLookupCacheModel).where(IsbnLookupCacheModel.isbn == isbn))
		model = result.scalar_one_or_none()
		return self._to_entity(model) if model else None

	async def save(self, entity: IsbnLookupCache) -> IsbnLookupCache:
		stmt = pg_insert(IsbnLookupCacheModel).values(
			isbn=entity.isbn,
			cache_metadata=entity.metadata,
			source=entity.source,
			fetched_at=entity.fetched_at,
		).on_conflict_do_update(
			index_elements=["isbn"],
			set_={
				"metadata": entity.metadata,
				"source": entity.source,
				"fetched_at": entity.fetched_at,
			},
		)
		await self._session.execute(stmt)
		result = await self._session.execute(
			select(IsbnLookupCacheModel).where(IsbnLookupCacheModel.isbn == entity.isbn)
		)
		model = result.scalar_one()
		return self._to_entity(model)
