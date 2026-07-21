from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.use_cases import (
	CreateBibliographicRecordInput,
	CreateBibliographicRecordUseCase,
	CreateCycleInput,
	CreateCycleUseCase,
	DeleteMeetingUseCase,
	GetCycleQuestionsInput,
	GetCycleQuestionsUseCase,
	GetCycleRatingSummaryUseCase,
	GetSharedHistoryUseCase,
	JoinCycleUseCase,
	ListMeetingsUseCase,
	ListParticipantsUseCase,
	ListProposalsUseCase,
	PromoteProposalUseCase,
	ProposeBookInput,
	ProposeBookUseCase,
	ScheduleMeetingInput,
	ScheduleMeetingUseCase,
	SetParticipantStatusUseCase,
	ToggleVoteUseCase,
)
from app.domain.entities import BookClubCycle, BookRating
from app.domain.entities.book_club_cycle import BookClubCycleStatus
from app.domain.entities.book_club_participant import ParticipantStatus
from app.domain.repositories import DiscussionBookContext, DiscussionQuestionGenerator


class FakeGenerator(DiscussionQuestionGenerator):
	def __init__(self, questions: list[str]) -> None:
		self.questions = questions
		self.calls = 0

	async def generate(self, ctx: DiscussionBookContext) -> list[str]:
		self.calls += 1
		return self.questions


async def _record(record_repo, library_id, title="Dune"):
	return await CreateBibliographicRecordUseCase(record_repo).execute(
		CreateBibliographicRecordInput(library_id=library_id, title=title)
	)


async def _cycle(cycle_repo, record_repo, book_repo, library_id, user_id, owned_book_id=None):
	rec = await _record(record_repo, library_id)
	return await CreateCycleUseCase(cycle_repo, record_repo, book_repo).execute(
		CreateCycleInput(
			library_id=library_id,
			created_by=user_id,
			bibliographic_record_id=rec.id,
			title="Cycle",
			owned_book_id=owned_book_id,
		)
	)


# ----- Proposals + voting -----


@pytest.mark.asyncio
async def test_propose_list_vote_toggle(proposal_repo, vote_repo, record_repo, test_library_id, test_user_id):
	rec = await _record(record_repo, test_library_id)
	proposal = await ProposeBookUseCase(proposal_repo, record_repo).execute(
		ProposeBookInput(
			library_id=test_library_id, proposed_by=test_user_id, bibliographic_record_id=rec.id
		)
	)

	listed = await ListProposalsUseCase(proposal_repo, vote_repo).execute(test_library_id, test_user_id)
	assert listed[0].vote_count == 0
	assert listed[0].voted_by_me is False

	voted = await ToggleVoteUseCase(proposal_repo, vote_repo).execute(
		proposal.id, test_library_id, test_user_id
	)
	assert voted is True
	listed = await ListProposalsUseCase(proposal_repo, vote_repo).execute(test_library_id, test_user_id)
	assert listed[0].vote_count == 1
	assert listed[0].voted_by_me is True

	voted = await ToggleVoteUseCase(proposal_repo, vote_repo).execute(
		proposal.id, test_library_id, test_user_id
	)
	assert voted is False
	listed = await ListProposalsUseCase(proposal_repo, vote_repo).execute(test_library_id, test_user_id)
	assert listed[0].vote_count == 0


@pytest.mark.asyncio
async def test_propose_rejects_other_library(proposal_repo, record_repo, test_library_id, test_user_id):
	rec = await _record(record_repo, uuid4())
	with pytest.raises(PermissionError):
		await ProposeBookUseCase(proposal_repo, record_repo).execute(
			ProposeBookInput(
				library_id=test_library_id, proposed_by=test_user_id, bibliographic_record_id=rec.id
			)
		)


@pytest.mark.asyncio
async def test_promote_creates_cycle_and_clears_pool(
	proposal_repo, vote_repo, cycle_repo, record_repo, test_library_id, test_user_id
):
	rec = await _record(record_repo, test_library_id)
	proposal = await ProposeBookUseCase(proposal_repo, record_repo).execute(
		ProposeBookInput(
			library_id=test_library_id, proposed_by=test_user_id, bibliographic_record_id=rec.id
		)
	)
	await ToggleVoteUseCase(proposal_repo, vote_repo).execute(proposal.id, test_library_id, test_user_id)

	cycle = await PromoteProposalUseCase(proposal_repo, cycle_repo, record_repo).execute(
		proposal.id, test_library_id, test_user_id
	)
	assert cycle.status is BookClubCycleStatus.READING
	assert cycle.bibliographic_record_id == rec.id
	assert await proposal_repo.list_by_library(test_library_id) == []


# ----- Participation -----


@pytest.mark.asyncio
async def test_join_is_idempotent_and_status(
	cycle_repo, participant_repo, record_repo, book_repo, test_library_id, test_user_id
):
	cycle = await _cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id)

	p1 = await JoinCycleUseCase(cycle_repo, participant_repo).execute(cycle.id, test_library_id, test_user_id)
	p2 = await JoinCycleUseCase(cycle_repo, participant_repo).execute(cycle.id, test_library_id, test_user_id)
	assert p1.id == p2.id

	updated = await SetParticipantStatusUseCase(cycle_repo, participant_repo).execute(
		cycle.id, test_library_id, test_user_id, ParticipantStatus.FINISHED
	)
	assert updated.status is ParticipantStatus.FINISHED

	participants = await ListParticipantsUseCase(cycle_repo, participant_repo).execute(cycle.id, test_library_id)
	assert len(participants) == 1


@pytest.mark.asyncio
async def test_set_status_without_join_raises(
	cycle_repo, participant_repo, record_repo, book_repo, test_library_id, test_user_id
):
	cycle = await _cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id)
	with pytest.raises(LookupError):
		await SetParticipantStatusUseCase(cycle_repo, participant_repo).execute(
			cycle.id, test_library_id, test_user_id, ParticipantStatus.FINISHED
		)


# ----- Meetings -----


@pytest.mark.asyncio
async def test_schedule_list_delete_meeting(
	cycle_repo, meeting_repo, record_repo, book_repo, test_library_id, test_user_id
):
	cycle = await _cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id)
	meeting = await ScheduleMeetingUseCase(cycle_repo, meeting_repo).execute(
		ScheduleMeetingInput(
			cycle_id=cycle.id,
			library_id=test_library_id,
			created_by=test_user_id,
			scheduled_at=datetime(2026, 8, 1, 18, 0, tzinfo=UTC),
			note="Library, room 2",
		)
	)
	listed = await ListMeetingsUseCase(cycle_repo, meeting_repo).execute(cycle.id, test_library_id)
	assert [m.id for m in listed] == [meeting.id]

	await DeleteMeetingUseCase(cycle_repo, meeting_repo).execute(meeting.id, test_library_id)
	assert await ListMeetingsUseCase(cycle_repo, meeting_repo).execute(cycle.id, test_library_id) == []


@pytest.mark.asyncio
async def test_meeting_wrong_library_rejected(
	cycle_repo, meeting_repo, record_repo, book_repo, test_library_id, test_user_id
):
	cycle = await _cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id)
	with pytest.raises(PermissionError):
		await ScheduleMeetingUseCase(cycle_repo, meeting_repo).execute(
			ScheduleMeetingInput(
				cycle_id=cycle.id,
				library_id=uuid4(),
				created_by=test_user_id,
				scheduled_at=datetime(2026, 8, 1, tzinfo=UTC),
			)
		)


# ----- AI discussion questions (CLUB-08) -----


@pytest.mark.asyncio
async def test_questions_get_or_generate_caches(
	cycle_repo, question_set_repo, record_repo, book_repo, test_library_id, test_user_id
):
	cycle = await _cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id)
	gen = FakeGenerator(["Q1?", "Q2?"])
	uc = GetCycleQuestionsUseCase(cycle_repo, record_repo, question_set_repo, gen)

	first = await uc.execute(
		GetCycleQuestionsInput(cycle_id=cycle.id, library_id=test_library_id, reader_language="it")
	)
	second = await uc.execute(
		GetCycleQuestionsInput(cycle_id=cycle.id, library_id=test_library_id, reader_language="it")
	)
	assert first == ["Q1?", "Q2?"]
	assert second == ["Q1?", "Q2?"]
	assert gen.calls == 1  # cached, LLM not re-called

	# A different reader language generates a fresh set (not the cached one).
	await uc.execute(
		GetCycleQuestionsInput(cycle_id=cycle.id, library_id=test_library_id, reader_language="en")
	)
	assert gen.calls == 2


@pytest.mark.asyncio
async def test_questions_empty_when_ai_off(
	cycle_repo, question_set_repo, record_repo, book_repo, test_library_id, test_user_id
):
	cycle = await _cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id)
	gen = FakeGenerator([])
	questions = await GetCycleQuestionsUseCase(cycle_repo, record_repo, question_set_repo, gen).execute(
		GetCycleQuestionsInput(cycle_id=cycle.id, library_id=test_library_id)
	)
	assert questions == []
	assert await question_set_repo.find_by_cycle_and_language(cycle.id, "") is None


# ----- Rating summary + shared history -----


@pytest.mark.asyncio
async def test_cycle_rating_summary(
	cycle_repo, book_rating_repo, record_repo, book_repo, test_library_id, test_user_id
):
	owned_book_id = uuid4()
	rec = await _record(record_repo, test_library_id)
	cycle = await cycle_repo.add(
		BookClubCycle(
			library_id=test_library_id,
			bibliographic_record_id=rec.id,
			title="Cycle",
			created_by=test_user_id,
			owned_book_id=owned_book_id,
		)
	)
	await book_rating_repo.add(BookRating(owned_book_id=owned_book_id, user_id=test_user_id, rating=4))
	await book_rating_repo.add(BookRating(owned_book_id=owned_book_id, user_id=uuid4(), rating=2))

	summary = await GetCycleRatingSummaryUseCase(cycle_repo, book_rating_repo).execute(
		cycle.id, test_library_id
	)
	assert summary.total == 2
	assert summary.average == 3.0


@pytest.mark.asyncio
async def test_shared_history_only_archived(
	cycle_repo, participant_repo, book_rating_repo, book_repo, record_repo, test_library_id, test_user_id
):
	active = await _cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id)
	archived = await _cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id)
	archived.status = BookClubCycleStatus.ARCHIVED
	await cycle_repo.save(archived)
	await JoinCycleUseCase(cycle_repo, participant_repo).execute(archived.id, test_library_id, test_user_id)

	entries = await GetSharedHistoryUseCase(
		cycle_repo, participant_repo, book_rating_repo, book_repo
	).execute(test_library_id)

	assert [e.cycle.id for e in entries] == [archived.id]
	assert entries[0].participant_count == 1
	assert active.id not in [e.cycle.id for e in entries]
