import logging

import httpx

from app.domain.repositories.tag_suggester import TagSuggester, TagSuggestion

logger = logging.getLogger(__name__)


class AiTagsClient(TagSuggester):
    def __init__(self, http_client: httpx.AsyncClient, ai_service_url: str) -> None:
        self._http_client = http_client
        self._ai_service_url = ai_service_url

    async def suggest(
        self,
        title: str,
        main_author: str | None,
        genre: str | None,
        reader_language: str | None = None,
    ) -> TagSuggestion:
        try:
            response = await self._http_client.post(
                f"{self._ai_service_url}/v1/suggestions/tags",
                json={
                    "title": title,
                    "main_author": main_author,
                    "genre": genre,
                    "reader_language": reader_language,
                },
            )
            response.raise_for_status()
            data = response.json()
            return TagSuggestion(tags=data.get("tags", []))
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("ai-service tag suggestion failed: %s", exc)
            return TagSuggestion(tags=[])
