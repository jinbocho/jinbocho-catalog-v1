from dataclasses import dataclass
from typing import Any

import httpx

from app.application.use_cases.ingestion.lookup_isbn import LookupIsbnUseCase
from app.domain.repositories import IsbnLookupCacheRepository


@dataclass
class BulkLookupIsbnResult:
	isbn: str
	ok: bool
	data: dict[str, Any] | None
	error: str | None


class BulkLookupIsbnUseCase:
	def __init__(self, cache_repo: IsbnLookupCacheRepository, http_client: httpx.AsyncClient | None = None) -> None:
		self._cache_repo = cache_repo
		self._http_client = http_client

	async def execute(self, isbns: list[str]) -> list[BulkLookupIsbnResult]:
		results: list[BulkLookupIsbnResult] = []
		for isbn in isbns:
			try:
				result = await LookupIsbnUseCase(self._cache_repo, self._http_client).execute(isbn)
				results.append(BulkLookupIsbnResult(isbn=isbn, ok=True, data=result.metadata, error=None))
			except LookupError:
				results.append(BulkLookupIsbnResult(isbn=isbn, ok=False, data=None, error="No metadata found"))
		return results
