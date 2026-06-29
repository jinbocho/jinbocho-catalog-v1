from dataclasses import dataclass
from typing import Any

from app.application.use_cases.ingestion.lookup_isbn import LookupIsbnUseCase
from app.domain.repositories import IsbnLookupCacheRepository, IsbnMetadataFetcher


@dataclass
class BulkLookupIsbnResult:
    isbn: str
    ok: bool
    data: dict[str, Any] | None
    error: str | None


class BulkLookupIsbnUseCase:
    def __init__(
        self,
        cache_repo: IsbnLookupCacheRepository,
        fetcher: IsbnMetadataFetcher,
        ttl_days: int = 30,
    ) -> None:
        self._cache_repo = cache_repo
        self._fetcher = fetcher
        self._ttl_days = ttl_days

    async def execute(self, isbns: list[str]) -> list[BulkLookupIsbnResult]:
        results: list[BulkLookupIsbnResult] = []
        for isbn in isbns:
            try:
                result = await LookupIsbnUseCase(self._cache_repo, self._fetcher, self._ttl_days).execute(isbn)
                results.append(BulkLookupIsbnResult(isbn=isbn, ok=True, data=result.metadata, error=None))
            except LookupError:
                results.append(BulkLookupIsbnResult(isbn=isbn, ok=False, data=None, error="No metadata found"))
        return results
