import logging

import httpx

from app.config import settings
from app.domain.repositories import DuplicateCandidate, DuplicateJudge, DuplicateJudgement

logger = logging.getLogger(__name__)


class HttpDuplicateJudge(DuplicateJudge):
	"""Asks ai-service's LLM whether two ambiguous-fuzzy-match candidates are
	the same work. Server-to-server only — never blocks adding a book on a
	network/LLM problem, degrades to "not a duplicate" instead (the textual
	fuzzy pre-filter in AddBookUseCase already keeps false negatives rare)."""

	def __init__(self, http_client: httpx.AsyncClient) -> None:
		self._http_client = http_client

	async def judge(
		self, candidate_a: DuplicateCandidate, candidate_b: DuplicateCandidate
	) -> DuplicateJudgement:
		if not settings.ai_module_enabled:
			return DuplicateJudgement(is_duplicate=False, confidence=0.0, reason="AI module not enabled")

		try:
			response = await self._http_client.post(
				f"{settings.ai_service_url}/v1/suggestions/dedup",
				headers={"X-Internal-Token": settings.ai_internal_service_token},
				json={
					"candidate_a": {
						"title": candidate_a.title,
						"main_author": candidate_a.main_author,
						"publication_year": candidate_a.publication_year,
					},
					"candidate_b": {
						"title": candidate_b.title,
						"main_author": candidate_b.main_author,
						"publication_year": candidate_b.publication_year,
					},
				},
			)
			response.raise_for_status()
			data = response.json()
			return DuplicateJudgement(
				is_duplicate=bool(data.get("is_duplicate", False)),
				confidence=float(data.get("confidence", 0.0)),
				reason=str(data.get("reason", "")),
			)
		except (httpx.HTTPError, ValueError) as exc:
			logger.warning("ai-service dedup check failed, treating as not a duplicate: %s", exc)
			return DuplicateJudgement(is_duplicate=False, confidence=0.0, reason="dedup check unavailable")
