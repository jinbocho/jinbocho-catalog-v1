import logging

import httpx

from app.domain.repositories.quiz_generator import GeneratedQuizQuestion, QuizBookContext, QuizGenerator
from app.infrastructure.external.ai_dedup_client import AiServiceConfig

logger = logging.getLogger(__name__)


class AiQuizClient(QuizGenerator):
	"""Asks ai-service's LLM for a comprehension quiz built from book metadata
	and an optional incipit. Server-to-server only — never blocks the child's
	quiz flow on a network/LLM problem, degrades to an empty list (the caller
	falls back to manually-authored questions) instead."""

	def __init__(self, http_client: httpx.AsyncClient, config: AiServiceConfig | None = None) -> None:
		self._http_client = http_client
		self._config = config if config is not None else AiServiceConfig()

	async def generate(self, ctx: QuizBookContext) -> list[GeneratedQuizQuestion]:
		if not self._config.enabled:
			return []

		try:
			response = await self._http_client.post(
				f"{self._config.url}/v1/suggestions/quiz",
				headers={"X-Internal-Token": self._config.internal_token},
				json={
					"title": ctx.title,
					"main_author": ctx.main_author,
					"genre": ctx.genre,
					"incipit": ctx.incipit,
					"language": ctx.language,
					"num_questions": ctx.num_questions,
					"extra_context": ctx.extra_context,
					"reader_age_band": ctx.reader_age_band,
					"reader_language": ctx.reader_language,
				},
				# The shared http_client defaults to a 10s timeout, but LLM quiz
				# generation (same provider/model as shelf-scan, see
				# ai_shelf_scan_client.py) routinely takes far longer than that —
				# every call was silently hitting ReadTimeout and falling back to
				# manual-only questions, with no error surfaced anywhere.
				timeout=120.0,
			)
			response.raise_for_status()
			data = response.json()
			raw_questions = data.get("questions", [])
			return [
				GeneratedQuizQuestion(
					prompt=str(q["prompt"]),
					choices=[str(c) for c in q["choices"]],
					correct_index=int(q["correct_index"]),
				)
				for q in raw_questions
				if isinstance(q, dict) and "prompt" in q and "choices" in q and "correct_index" in q
			]
		except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
			logger.warning("ai-service quiz generation failed, falling back to manual-only: %s", exc)
			return []
