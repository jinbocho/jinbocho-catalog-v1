from typing import Any

from app.infrastructure.external.http_isbn_metadata_fetcher import HttpIsbnMetadataFetcher


class FakeResponse:
	def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
		self._payload = payload
		self.status_code = status_code

	def raise_for_status(self) -> None:
		pass

	def json(self) -> dict[str, Any]:
		return self._payload


class RoutedHttpClient:
	"""Stands in for httpx.AsyncClient — routes by URL substring to a canned payload."""

	def __init__(self, routes: dict[str, dict[str, Any]]) -> None:
		self._routes = routes
		self.urls_called: list[str] = []

	async def get(self, url: str, params: dict[str, Any] | None = None) -> FakeResponse:
		self.urls_called.append(url)
		for key, payload in self._routes.items():
			if key in url:
				return FakeResponse(payload)
		return FakeResponse({})


async def test_accepts_google_books_result_when_no_expected_language() -> None:
	client = RoutedHttpClient(
		{
			"/volumes": {
				"items": [{"volumeInfo": {"title": "Some Title", "language": "en"}}],
			},
		}
	)
	fetcher = HttpIsbnMetadataFetcher(client)  # type: ignore[arg-type]

	result = await fetcher.fetch("978-0-13-468599-1")

	assert result is not None
	assert result.source == "google_books"
	assert result.metadata["title"] == "Some Title"


async def test_skips_google_books_wrong_language_for_italian_isbn_and_uses_open_library_search(
	monkeypatch: Any,
) -> None:
	client = RoutedHttpClient(
		{
			"/volumes": {
				"items": [{"volumeInfo": {"title": "English Title", "language": "en"}}],
			},
			"/api/books": {},
			"/search.json": {
				"docs": [
					{
						"title": "Titolo Italiano",
						"author_name": ["Autore"],
						"language": ["ita"],
					}
				]
			},
		}
	)
	fetcher = HttpIsbnMetadataFetcher(client)  # type: ignore[arg-type]

	# open_library_search reports its own language codes ("ita"), so make the
	# expected-language check line up with what that source actually returns.
	monkeypatch.setattr(
		"app.infrastructure.external.http_isbn_metadata_fetcher.expected_language_for_isbn",
		lambda isbn: "ita",
	)

	result = await fetcher.fetch("978-88-04-12345-6")

	assert result is not None
	assert result.source == "open_library_search"
	assert result.metadata["title"] == "Titolo Italiano"


async def test_falls_back_to_first_candidate_when_no_source_matches_expected_language(
	monkeypatch: Any,
) -> None:
	client = RoutedHttpClient(
		{
			"/volumes": {
				"items": [{"volumeInfo": {"title": "English Title", "language": "en"}}],
			},
			"/api/books": {},
			"/search.json": {"docs": []},
		}
	)
	fetcher = HttpIsbnMetadataFetcher(client)  # type: ignore[arg-type]

	monkeypatch.setattr(
		"app.infrastructure.external.http_isbn_metadata_fetcher.expected_language_for_isbn",
		lambda isbn: "it",
	)

	result = await fetcher.fetch("978-88-04-12345-6")

	assert result is not None
	assert result.source == "google_books"
	assert result.metadata["title"] == "English Title"
