import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import httpx

from app.application.use_cases.ingestion.google_books_mapper import extract_year, volume_to_metadata
from app.domain.entities import IsbnLookupCache
from app.domain.repositories import IsbnLookupCacheRepository
from app.utils import utcnow

logger = logging.getLogger(__name__)


@dataclass
class IsbnLookupConfig:
	ttl_days: int = 30
	google_books_url: str = "https://www.googleapis.com/books/v1"
	google_books_api_key: str = ""
	open_library_url: str = "https://openlibrary.org"


@dataclass
class LookupIsbnOutput:
	source: str
	metadata: dict[str, Any]
	cached: bool


class LookupIsbnUseCase:
	def __init__(
		self,
		cache_repo: IsbnLookupCacheRepository,
		http_client: httpx.AsyncClient | None = None,
		config: IsbnLookupConfig | None = None,
	) -> None:
		self._cache_repo = cache_repo
		self._http_client = http_client
		self._config = config if config is not None else IsbnLookupConfig()

	async def execute(self, isbn: str) -> LookupIsbnOutput:
		cached = await self._cache_repo.find_by_isbn(isbn)
		if cached and cached.fetched_at >= utcnow() - timedelta(days=self._config.ttl_days):
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

		open_library_search = await self._fetch_open_library_search(isbn)
		if open_library_search:
			await self._cache_repo.save(
				IsbnLookupCache(isbn=isbn, metadata=open_library_search, source="open_library_search", fetched_at=utcnow())
			)
			return LookupIsbnOutput(source="open_library_search", metadata=open_library_search, cached=False)

		raise LookupError(f"No metadata found for ISBN {isbn}")

	async def _fetch_google_books(self, isbn: str) -> dict[str, Any] | None:
		# Network/HTTP failures here must not abort the lookup — fall through to
		# the Open Library fallback instead of surfacing a 500.
		assert self._http_client is not None
		try:
			params: dict[str, str | int] = {"q": f"isbn:{isbn}", "maxResults": 1}
			if self._config.google_books_api_key:
				params["key"] = self._config.google_books_api_key
			response = await self._http_client.get(
				f"{self._config.google_books_url}/volumes",
				params=params,
			)
			if response.status_code in (429, 503):
				return None
			response.raise_for_status()
			data = response.json()
		except httpx.HTTPError:
			return None
		if not data.get("items"):
			return None
		volume = data["items"][0].get("volumeInfo", {})
		return volume_to_metadata(volume, isbn=isbn)

	async def _fetch_open_library(self, isbn: str) -> dict[str, Any] | None:
		assert self._http_client is not None
		try:
			response = await self._http_client.get(
				f"{self._config.open_library_url}/api/books",
				params={"bibkeys": f"ISBN:{isbn}", "format": "json", "jscmd": "data"},
			)
			response.raise_for_status()
			data = response.json()
		except httpx.HTTPError:
			return None
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
			"publication_year": extract_year(book.get("publish_date")),
			"language": None,
			"genre": None,
			"cover_url": (book.get("cover") or {}).get("medium") or (book.get("cover") or {}).get("large"),
			"notes": None,
			"isbn": isbn,
		}

	async def _fetch_open_library_search(self, isbn: str) -> dict[str, Any] | None:
		"""Fallback using Open Library /search.json — broader index than /api/books."""
		assert self._http_client is not None
		try:
			response = await self._http_client.get(
				f"{self._config.open_library_url}/search.json",
				params={"isbn": isbn, "fields": "title,author_name,publisher,first_publish_year,language,cover_i"},
			)
			response.raise_for_status()
			data = response.json()
		except httpx.HTTPError:
			return None
		docs = data.get("docs")
		if not docs:
			return None
		doc = docs[0]
		authors = doc.get("author_name") or []
		publishers = doc.get("publisher") or []
		cover_i = doc.get("cover_i")
		cover_url = f"https://covers.openlibrary.org/b/id/{cover_i}-M.jpg" if cover_i else None
		languages = doc.get("language") or []
		return {
			"title": doc.get("title"),
			"main_author": authors[0] if authors else None,
			"other_authors": authors[1:] if len(authors) > 1 else [],
			"publisher": publishers[0] if publishers else None,
			"publication_year": doc.get("first_publish_year"),
			"language": languages[0] if languages else None,
			"genre": None,
			"cover_url": cover_url,
			"notes": None,
			"isbn": isbn,
		}
