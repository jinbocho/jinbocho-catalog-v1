import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class AiIncipitResult:
    text: str | None
    model: str | None


class AiIncipitClient:
    def __init__(self, http_client: httpx.AsyncClient, ai_service_url: str) -> None:
        self._http_client = http_client
        self._ai_service_url = ai_service_url

    async def generate(
        self,
        title: str,
        main_author: str | None,
        genre: str | None,
        language: str | None,
        publisher: str | None,
        publication_year: int | None,
        editorial_description: str | None,
    ) -> AiIncipitResult:
        try:
            response = await self._http_client.post(
                f"{self._ai_service_url}/v1/suggestions/incipit",
                json={
                    "title": title,
                    "main_author": main_author,
                    "genre": genre,
                    "language": language,
                    "publisher": publisher,
                    "publication_year": publication_year,
                    "editorial_description": editorial_description,
                },
            )
            response.raise_for_status()
            data = response.json()
            return AiIncipitResult(text=data.get("text"), model=data.get("model"))
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("ai-service incipit generation failed: %s", exc)
            return AiIncipitResult(text=None, model=None)
