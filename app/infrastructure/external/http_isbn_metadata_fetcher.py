import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.domain.repositories.isbn_metadata_fetcher import IsbnFetchResult, IsbnMetadataFetcher
from app.infrastructure.external.google_books_mapper import extract_year, volume_to_metadata

logger = logging.getLogger(__name__)


@dataclass
class IsbnLookupConfig:
    google_books_url: str = "https://www.googleapis.com/books/v1"
    google_books_api_key: str = ""
    open_library_url: str = "https://openlibrary.org"


class HttpIsbnMetadataFetcher(IsbnMetadataFetcher):
    """Fetches ISBN metadata from Google Books (primary) with Open Library fallbacks.
    Fallback order: Google Books → Open Library /api/books → Open Library /search.json."""

    def __init__(self, http_client: httpx.AsyncClient, config: IsbnLookupConfig | None = None) -> None:
        self._http_client = http_client
        self._config = config or IsbnLookupConfig()

    async def fetch(self, isbn: str) -> IsbnFetchResult | None:
        google = await self._fetch_google_books(isbn)
        if google is not None:
            return IsbnFetchResult(source="google_books", metadata=google)

        ol = await self._fetch_open_library(isbn)
        if ol is not None:
            return IsbnFetchResult(source="open_library", metadata=ol)

        ol_search = await self._fetch_open_library_search(isbn)
        if ol_search is not None:
            return IsbnFetchResult(source="open_library_search", metadata=ol_search)

        return None

    async def _fetch_google_books(self, isbn: str) -> dict[str, Any] | None:
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
        authors = [a.get("name") for a in book.get("authors", []) if a.get("name")]
        publishers = [p.get("name") for p in book.get("publishers", []) if p.get("name")]
        return {
            "title": book.get("title"),
            "main_author": authors[0] if authors else None,
            "other_authors": authors[1:] if len(authors) > 1 else [],
            "publisher": publishers[0] if publishers else None,
            "publication_year": extract_year(book.get("publish_date")),
            "language": None,
            "genre": None,
            "cover_url": (book.get("cover") or {}).get("medium") or (book.get("cover") or {}).get("large"),
            "description": await self._fetch_open_library_description(isbn),
            "notes": None,
            "isbn": isbn,
        }

    async def _fetch_open_library_description(self, isbn: str) -> str | None:
        try:
            response = await self._http_client.get(
                f"{self._config.open_library_url}/api/books",
                params={"bibkeys": f"ISBN:{isbn}", "format": "json", "jscmd": "details"},
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError:
            return None
        details = data.get(f"ISBN:{isbn}", {}).get("details", {})
        raw = details.get("description")
        if not raw:
            return None
        if isinstance(raw, dict):
            return str(raw.get("value", "")).strip() or None
        return str(raw).strip() or None

    async def _fetch_open_library_search(self, isbn: str) -> dict[str, Any] | None:
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
