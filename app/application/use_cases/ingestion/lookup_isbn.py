import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Optional
from uuid import UUID

import httpx

from app.config import settings
from app.domain.entities import IsbnLookupCache
from app.domain.repositories import IsbnLookupCacheRepository
from app.utils import utcnow

logger = logging.getLogger(__name__)


@dataclass
class LookupIsbnOutput:
	source: str
	metadata: dict[str, Any]
	cached: bool


def _extract_year(value: Optional[str]) -> Optional[int]:
	if not value:
		return None
	for part in value.split("-"):
		if part[:4].isdigit():
			return int(part[:4])
	digits = "".join(ch for ch in value if ch.isdigit())
	if len(digits) >= 4:
		return int(digits[:4])
	return None


class LookupIsbnUseCase:
	def __init__(self, cache_repo: IsbnLookupCacheRepository, http_client: Optional[httpx.AsyncClient] = None) -> None:
		self._cache_repo = cache_repo
		self._http_client = http_client

	async def execute(self, isbn: str) -> LookupIsbnOutput:
		cached = await self._cache_repo.find_by_isbn(isbn)
		if cached and cached.fetched_at >= utcnow() - timedelta(days=settings.isbn_cache_ttl_days):
			return LookupIsbnOutput(source=cached.source, metadata=cached.metadata, cached=True)

		if self._http_client is None:
			raise RuntimeError("HTTP client not configured")

		google = await self._fetch_google_books(isbn)
		if google:
			await self._cache_repo.save(
				IsbnLookupCache(isbn=isbn, metadata=google, source="google_books", fetched_at=utcnow())
			)
			return LookupIsbnOutput(source="google_books", metadata=google, cached=False)

		open_library = await self._fetch_open_library(isbn)
		if open_library:
			await self._cache_repo.save(
				IsbnLookupCache(isbn=isbn, metadata=open_library, source="open_library", fetched_at=utcnow())
			)
			return LookupIsbnOutput(source="open_library", metadata=open_library, cached=False)

		raise LookupError(f"No metadata found for ISBN {isbn}")

	async def _fetch_google_books(self, isbn: str) -> Optional[dict[str, Any]]:
		response = await self._http_client.get(
			f"{settings.google_books_url}/volumes",
			params={"q": f"isbn:{isbn}", "maxResults": 1},
		)
		if response.status_code in (429, 503):
			return None
		response.raise_for_status()
		data = response.json()
		if not data.get("items"):
			return None
		volume = data["items"][0].get("volumeInfo", {})
		return {
			"title": volume.get("title"),
			"main_author": (volume.get("authors") or [None])[0],
			"other_authors": (volume.get("authors") or [])[1:],
			"publisher": volume.get("publisher"),
			"publication_year": _extract_year(volume.get("publishedDate")),
			"language": volume.get("language"),
			"genre": (volume.get("categories") or [None])[0],
			"cover_url": (volume.get("imageLinks") or {}).get("thumbnail"),
			"notes": volume.get("description"),
			"isbn": isbn,
		}

	async def _fetch_open_library(self, isbn: str) -> Optional[dict[str, Any]]:
		response = await self._http_client.get(
			f"{settings.open_library_url}/api/books",
			params={"bibkeys": f"ISBN:{isbn}", "format": "json", "jscmd": "data"},
		)
		response.raise_for_status()
		data = response.json()
		book = data.get(f"ISBN:{isbn}")
		if not book:
			return None
		authors = [author.get("name") for author in book.get("authors", []) if author.get("name")]
		publishers = [publisher.get("name") for publisher in book.get("publishers", []) if publisher.get("name")]
		return {
			"title": book.get("title"),
			"main_author": authors[0] if authors else None,
			"other_authors": authors[1:] if len(authors) > 1 else [],
			"publisher": publishers[0] if publishers else None,
			"publication_year": _extract_year(book.get("publish_date")),
			"language": None,
			"genre": None,
			"cover_url": (book.get("cover") or {}).get("medium") or (book.get("cover") or {}).get("large"),
			"notes": None,
			"isbn": isbn,
		}
