from abc import ABC, abstractmethod

from app.domain.entities import IsbnLookupCache


class IsbnLookupCacheRepository(ABC):
	@abstractmethod
	async def find_by_isbn(self, isbn: str) -> IsbnLookupCache | None: ...

	@abstractmethod
	async def save(self, entity: IsbnLookupCache) -> IsbnLookupCache: ...
