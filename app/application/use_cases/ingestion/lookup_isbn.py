from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from app.domain.entities import IsbnLookupCache
from app.domain.repositories import IsbnLookupCacheRepository, IsbnMetadataFetcher
from app.utils import utcnow


@dataclass
class LookupIsbnOutput:
    source: str
    metadata: dict[str, Any]
    cached: bool


class LookupIsbnUseCase:
    def __init__(
        self,
        cache_repo: IsbnLookupCacheRepository,
        fetcher: IsbnMetadataFetcher,
        ttl_days: int = 30,
    ) -> None:
        self._cache_repo = cache_repo
        self._fetcher = fetcher
        self._ttl_days = ttl_days

    async def execute(self, isbn: str) -> LookupIsbnOutput:
        cached = await self._cache_repo.find_by_isbn(isbn)
        if cached and cached.fetched_at >= utcnow() - timedelta(days=self._ttl_days):
            return LookupIsbnOutput(source=cached.source, metadata=cached.metadata, cached=True)

        result = await self._fetcher.fetch(isbn)
        if result is None:
            raise LookupError(f"No metadata found for ISBN {isbn}")

        await self._cache_repo.save(
            IsbnLookupCache(isbn=isbn, metadata=result.metadata, source=result.source, fetched_at=utcnow())
        )
        return LookupIsbnOutput(source=result.source, metadata=result.metadata, cached=False)
