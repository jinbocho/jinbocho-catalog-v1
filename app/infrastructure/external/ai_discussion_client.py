import logging

import httpx

from app.domain.repositories.discussion_generator import DiscussionBookContext, DiscussionQuestionGenerator
from app.infrastructure.external.ai_dedup_client import AiServiceConfig

logger = logging.getLogger(__name__)


class AiDiscussionClient(DiscussionQuestionGenerator):
	"""Asks ai-service's LLM for dinner-table conversation questions (KID-04),
	built from book metadata and an optional incipit. Server-to-server only —
	never blocks the parent dashboard on a network/LLM problem, degrades to an
	empty list (caller shows no card) instead."""

	def __init__(self, http_client: httpx.AsyncClient, config: AiServiceConfig | None = None) -> None:
		self._http_client = http_client
		self._config = config if config is not None else AiServiceConfig()

	async def generate(self, ctx: DiscussionBookContext) -> list[str]:
		if not self._config.enabled:
			return []

		try:
			response = await self._http_client.post(
				f"{self._config.url}/v1/suggestions/discussion",
				headers={"X-Internal-Token": self._config.internal_token},
				json={
					"title": ctx.title,
					"main_author": ctx.main_author,
					"genre": ctx.genre,
					"incipit": ctx.incipit,
					"language": ctx.language,
					"num_questions": ctx.num_questions,
					"reader_age_band": ctx.reader_age_band,
					"reader_language": ctx.reader_language,
				},
				# Same rationale as AiQuizClient: the shared http_client's default
				# 10s timeout is far shorter than real LLM generation latency.
				timeout=120.0,
			)
			response.raise_for_status()
			data = response.json()
			raw_questions = data.get("questions", [])
			return [str(q).strip() for q in raw_questions if isinstance(q, str) and q.strip()]
		except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
			logger.warning("ai-service discussion generation failed, hiding the card: %s", exc)
			return []
