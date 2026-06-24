import pytest

from app.application.use_cases.catalog.add_book import AddBookInput, AddBookUseCase, DuplicateBookError
from app.domain.repositories import DuplicateCandidate, DuplicateJudge, DuplicateJudgement


class FakeDuplicateJudge(DuplicateJudge):
	"""Records whether it was called, and returns a fixed verdict — used to
	assert the ambiguous-band LLM call only happens when the fuzzy pre-filter
	actually lands in that band, never above/below it."""

	def __init__(self, verdict: DuplicateJudgement) -> None:
		self.verdict = verdict
		self.calls: list[tuple[DuplicateCandidate, DuplicateCandidate]] = []

	async def judge(self, candidate_a: DuplicateCandidate, candidate_b: DuplicateCandidate) -> DuplicateJudgement:
		self.calls.append((candidate_a, candidate_b))
		return self.verdict


class ExplodingDuplicateJudge(DuplicateJudge):
	"""Fails the test if invoked — for asserting a code path never reaches
	the network call (e.g. clearly-distinct titles, or a confident fuzzy match
	that should skip straight to a conflict)."""

	async def judge(self, candidate_a: DuplicateCandidate, candidate_b: DuplicateCandidate) -> DuplicateJudgement:
		raise AssertionError("DuplicateJudge.judge() should not have been called")


@pytest.mark.asyncio
async def test_no_judge_means_no_fuzzy_check(
	record_repo, book_repo, history_repo, cache_repo, book_read_repo, test_family_id, test_user_id
):
	"""Existing behaviour is preserved when dedup_judge is omitted (default
	None) — exact checks only, identical to before this feature existed."""
	use_case = AddBookUseCase(record_repo, book_repo, history_repo, cache_repo, book_read_repo)
	await use_case.execute(
		AddBookInput(family_id=test_family_id, changed_by=test_user_id, title="Dune", main_author="Frank Herbert")
	)

	# Clearly similar but not exact — would be a fuzzy match if a judge were wired.
	book = await use_case.execute(
		AddBookInput(family_id=test_family_id, changed_by=test_user_id, title="Dune!", main_author="Frank Herbert")
	)
	assert book is not None


@pytest.mark.asyncio
async def test_clearly_distinct_titles_never_call_the_judge(
	record_repo, book_repo, history_repo, cache_repo, book_read_repo, test_family_id, test_user_id
):
	judge = ExplodingDuplicateJudge()
	use_case = AddBookUseCase(record_repo, book_repo, history_repo, cache_repo, book_read_repo, dedup_judge=judge)
	await use_case.execute(
		AddBookInput(family_id=test_family_id, changed_by=test_user_id, title="Dune", main_author="Frank Herbert")
	)

	book = await use_case.execute(
		AddBookInput(
			family_id=test_family_id, changed_by=test_user_id, title="The Hobbit", main_author="J.R.R. Tolkien"
		)
	)
	assert book is not None


@pytest.mark.asyncio
async def test_ambiguous_band_calls_judge_and_flags_when_duplicate(
	record_repo, book_repo, history_repo, cache_repo, book_read_repo, test_family_id, test_user_id
):
	judge = FakeDuplicateJudge(
		DuplicateJudgement(is_duplicate=True, confidence=0.8, reason="Same novel, different printing")
	)
	use_case = AddBookUseCase(record_repo, book_repo, history_repo, cache_repo, book_read_repo, dedup_judge=judge)
	await use_case.execute(
		AddBookInput(family_id=test_family_id, changed_by=test_user_id, title="Dune", main_author="Frank Herbert")
	)

	# Same author, title similar enough to land in the ambiguous band but not
	# an exact/near-exact string match.
	with pytest.raises(DuplicateBookError) as exc_info:
		await use_case.execute(
			AddBookInput(
				family_id=test_family_id,
				changed_by=test_user_id,
				title="Dune (40th Anniversary Ed.)",
				main_author="Frank Herbert",
			)
		)

	assert exc_info.value.conflict.conflict_type == "fuzzy_match"
	assert exc_info.value.conflict.match_reason == "Same novel, different printing"
	assert len(judge.calls) == 1


@pytest.mark.asyncio
async def test_ambiguous_band_proceeds_when_judge_says_not_duplicate(
	record_repo, book_repo, history_repo, cache_repo, book_read_repo, test_family_id, test_user_id
):
	judge = FakeDuplicateJudge(DuplicateJudgement(is_duplicate=False, confidence=0.2, reason="Different books"))
	use_case = AddBookUseCase(record_repo, book_repo, history_repo, cache_repo, book_read_repo, dedup_judge=judge)
	await use_case.execute(
		AddBookInput(family_id=test_family_id, changed_by=test_user_id, title="Dune", main_author="Frank Herbert")
	)

	book = await use_case.execute(
		AddBookInput(
			family_id=test_family_id,
			changed_by=test_user_id,
			title="Dune (40th Anniversary Ed.)",
			main_author="Frank Herbert",
		)
	)
	assert book is not None
	assert len(judge.calls) == 1


@pytest.mark.asyncio
async def test_high_confidence_fuzzy_match_skips_the_judge_entirely(
	record_repo, book_repo, history_repo, cache_repo, book_read_repo, test_family_id, test_user_id
):
	"""A near-identical title/author (above the high threshold) is confident
	enough on its own — no network round-trip to ai-service needed."""
	judge = ExplodingDuplicateJudge()
	use_case = AddBookUseCase(record_repo, book_repo, history_repo, cache_repo, book_read_repo, dedup_judge=judge)
	await use_case.execute(
		AddBookInput(family_id=test_family_id, changed_by=test_user_id, title="Dune", main_author="Frank Herbert")
	)

	with pytest.raises(DuplicateBookError) as exc_info:
		await use_case.execute(
			AddBookInput(family_id=test_family_id, changed_by=test_user_id, title="dune", main_author="Frank Herbert")
		)

	assert exc_info.value.conflict.conflict_type == "fuzzy_match"
	assert exc_info.value.conflict.match_reason is None
