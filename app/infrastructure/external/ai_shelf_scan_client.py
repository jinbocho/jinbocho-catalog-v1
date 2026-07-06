import logging

import httpx

from app.config import settings
from app.domain.repositories.shelf_spine_reader import ShelfSpineReader, SpineReading, SpineReadResult

logger = logging.getLogger(__name__)


class AiShelfScanClient(ShelfSpineReader):
	"""Asks ai-service's vision LLM to read book spines from a shelf photo.
	Server-to-server only, like HttpDuplicateJudge. Propagates the AI service's
	``reason`` so the caller can distinguish a disabled module, a model that
	can't read images, and a transient failure — and never blocks on a problem."""

	def __init__(self, http_client: httpx.AsyncClient, ai_service_url: str) -> None:
		self._http_client = http_client
		self._ai_service_url = ai_service_url

	async def read_spines(self, image_base64: str, media_type: str) -> SpineReadResult:
		if not settings.ai_module_enabled:
			return SpineReadResult(available=False, reason="disabled")

		try:
			response = await self._http_client.post(
				f"{self._ai_service_url}/v1/suggestions/shelf-scan",
				headers={"X-Internal-Token": settings.ai_internal_service_token},
				json={"image_base64": image_base64, "media_type": media_type},
				# A real shelf with 15-20+ spines takes highly variable time for
				# the vision model to read — observed 62s for 17 spines and 138s
				# for 19 spines on the same model/provider, so the variance isn't
				# just proportional to spine count. 240s gives real margin above
				# the worst case actually measured, not just the best case.
				timeout=240.0,
			)
			response.raise_for_status()
			data = response.json()
		except (httpx.HTTPError, ValueError) as exc:
			logger.warning("ai-service shelf scan failed: %s", exc)
			return SpineReadResult(available=False, reason="error")

		if not data.get("available", False):
			return SpineReadResult(available=False, reason=str(data.get("reason", "error")))
		spines = [
			SpineReading(
				title=str(spine.get("title", "")),
				author=spine.get("author"),
				position=int(spine.get("position", index)),
			)
			for index, spine in enumerate(data.get("spines", []))
			if spine.get("title")
		]
		return SpineReadResult(available=True, reason="ok", spines=spines)
