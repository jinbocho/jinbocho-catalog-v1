import logging

import httpx

from app.domain.repositories.editorial_description_provider import EditorialDescriptionProvider

logger = logging.getLogger(__name__)

_TIMEOUT = 5.0


class OpenLibraryDescriptionFetcher(EditorialDescriptionProvider):
    def __init__(self, http_client: httpx.AsyncClient, open_library_url: str) -> None:
        self._http_client = http_client
        self._open_library_url = open_library_url

    async def fetch(self, isbn: str) -> str | None:
        try:
            response = await self._http_client.get(
                f"{self._open_library_url}/api/books",
                params={"bibkeys": f"ISBN:{isbn}", "format": "json", "jscmd": "details"},
                timeout=_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError):
            return None

        details = data.get(f"ISBN:{isbn}", {}).get("details", {})
        raw = details.get("description")
        if not raw:
            return None
        if isinstance(raw, dict):
            return str(raw.get("value", "")).strip() or None
        return str(raw).strip() or None
