import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.domain.repositories.book_search_provider import BookSearchProvider
from app.infrastructure.external.google_books_mapper import volume_to_metadata

logger = logging.getLogger(__name__)


@dataclass
class BookSearchConfig:
    google_books_url: str = "https://www.googleapis.com/books/v1"
    google_books_api_key: str = ""
    open_library_url: str = "https://openlibrary.org"


class HttpBookSearchProvider(BookSearchProvider):
    """Searches books via Google Books (primary) with Open Library fallback."""

    def __init__(self, http_client: httpx.AsyncClient, config: BookSearchConfig | None = None) -> None:
        self._http_client = http_client
        self._config = config or BookSearchConfig()

    async def search(
        self,
        title: str | None,
        author: str | None,
        max_results: int,
    ) -> list[dict[str, Any]]:
        results = await self._search_google_books(title, author, max_results)
        if results:
            return results
        return await self._search_open_library(title, author, max_results)

    async def _search_google_books(
        self, title: str | None, author: str | None, max_results: int
    ) -> list[dict[str, Any]]:
        terms = []
        if title:
            terms.append(f"intitle:{title}")
        if author:
            terms.append(f"inauthor:{author}")

        params: dict[str, str | int] = {"q": "+".join(terms), "maxResults": max_results}
        if self._config.google_books_api_key:
            params["key"] = self._config.google_books_api_key

        try:
            response = await self._http_client.get(
                f"{self._config.google_books_url}/volumes", params=params
            )
            if response.status_code in (429, 503):
                return []
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError:
            return []

        results: list[dict[str, Any]] = []
        for item in data.get("items", []):
            volume = item.get("volumeInfo", {})
            if not volume.get("title"):
                continue
            results.append(volume_to_metadata(volume))
        return results

    async def _search_open_library(
        self, title: str | None, author: str | None, max_results: int
    ) -> list[dict[str, Any]]:
        params: dict[str, str | int] = {
            "fields": "title,author_name,publisher,first_publish_year,language,cover_i,isbn",
            "limit": max_results,
        }
        if title:
            params["title"] = title
        if author:
            params["author"] = author

        try:
            response = await self._http_client.get(
                f"{self._config.open_library_url}/search.json", params=params
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError:
            return []

        results: list[dict[str, Any]] = []
        for doc in data.get("docs", []):
            if not doc.get("title"):
                continue
            results.append(self._doc_to_metadata(doc))
        return results

    @staticmethod
    def _doc_to_metadata(doc: dict[str, Any]) -> dict[str, Any]:
        authors = doc.get("author_name") or []
        publishers = doc.get("publisher") or []
        isbns = doc.get("isbn") or []
        languages = doc.get("language") or []
        cover_i = doc.get("cover_i")
        return {
            "title": doc.get("title"),
            "main_author": authors[0] if authors else None,
            "other_authors": authors[1:],
            "publisher": publishers[0] if publishers else None,
            "publication_year": doc.get("first_publish_year"),
            "language": languages[0] if languages else None,
            "genre": None,
            "cover_url": f"https://covers.openlibrary.org/b/id/{cover_i}-M.jpg" if cover_i else None,
            "notes": None,
            "isbn": isbns[0] if isbns else None,
        }
