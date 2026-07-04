import pytest

from app.domain.repositories import DuplicateCandidate
from app.infrastructure.external.ai_dedup_client import AiServiceConfig, HttpDuplicateJudge


class ExplodingHttpClient:
	"""Stands in for httpx.AsyncClient — fails the test if a request is ever made."""

	async def post(self, *args: object, **kwargs: object) -> None:
		raise AssertionError("HTTP call should not have been made when the ai module is disabled")


class RecordingHttpClient:
	"""Stands in for httpx.AsyncClient — captures the request instead of making one."""

	def __init__(self, response_json: dict[str, object]) -> None:
		self.calls: list[tuple[str, dict[str, str]]] = []
		self._response_json = response_json

	async def post(self, url: str, headers: dict[str, str], json: dict[str, object]) -> "_FakeResponse":
		self.calls.append((url, headers))
		return _FakeResponse(self._response_json)


class _FakeResponse:
	def __init__(self, payload: dict[str, object]) -> None:
		self._payload = payload

	def raise_for_status(self) -> None:
		pass

	def json(self) -> dict[str, object]:
		return self._payload


@pytest.mark.asyncio
async def test_skips_http_call_when_ai_module_disabled() -> None:
	judge = HttpDuplicateJudge(ExplodingHttpClient(), AiServiceConfig(enabled=False))  # type: ignore[arg-type]

	result = await judge.judge(
		DuplicateCandidate(title="Dune", main_author="Frank Herbert", publication_year=1965),
		DuplicateCandidate(title="Dune (different printing)", main_author="Frank Herbert", publication_year=1990),
	)

	assert result.is_duplicate is False
	assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_calls_ai_service_with_configured_url_and_token_when_enabled() -> None:
	http_client = RecordingHttpClient({"is_duplicate": True, "confidence": 0.95, "reason": "same work"})
	config = AiServiceConfig(enabled=True, url="http://jinbocho-ai:8003", internal_token="s3cr3t")
	judge = HttpDuplicateJudge(http_client, config)  # type: ignore[arg-type]

	result = await judge.judge(
		DuplicateCandidate(title="Dune", main_author="Frank Herbert", publication_year=1965),
		DuplicateCandidate(title="Dune (different printing)", main_author="Frank Herbert", publication_year=1990),
	)

	assert result.is_duplicate is True
	assert result.confidence == 0.95
	assert len(http_client.calls) == 1
	url, headers = http_client.calls[0]
	assert url == "http://jinbocho-ai:8003/v1/suggestions/dedup"
	assert headers == {"X-Internal-Token": "s3cr3t"}
