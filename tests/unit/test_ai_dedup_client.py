import pytest

from app.config import settings
from app.domain.repositories import DuplicateCandidate
from app.infrastructure.external.ai_dedup_client import HttpDuplicateJudge


class ExplodingHttpClient:
	"""Stands in for httpx.AsyncClient — fails the test if a request is ever made."""

	async def post(self, *args: object, **kwargs: object) -> None:
		raise AssertionError("HTTP call should not have been made when the ai module is disabled")


@pytest.mark.asyncio
async def test_skips_http_call_when_ai_module_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(settings, "jinbocho_features", "catalog,auth")
	judge = HttpDuplicateJudge(ExplodingHttpClient())  # type: ignore[arg-type]

	result = await judge.judge(
		DuplicateCandidate(title="Dune", main_author="Frank Herbert", publication_year=1965),
		DuplicateCandidate(title="Dune (different printing)", main_author="Frank Herbert", publication_year=1990),
	)

	assert result.is_duplicate is False
	assert result.confidence == 0.0
