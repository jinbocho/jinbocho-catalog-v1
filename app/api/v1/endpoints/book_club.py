from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_bibliographic_record_repository,
    get_book_club_cycle_repository,
    get_book_club_meeting_repository,
    get_book_club_participant_repository,
    get_book_club_post_repository,
    get_book_club_proposal_repository,
    get_book_club_question_set_repository,
    get_book_club_vote_repository,
    get_book_rating_repository,
    get_discussion_generator,
    get_owned_book_repository,
    require_role,
)
from app.api.v1.schemas.book_club_schemas import (
    CycleAdvance,
    CycleCreate,
    CycleRatingResponse,
    CycleResponse,
    HistoryEntryResponse,
    MeetingCreate,
    MeetingResponse,
    ParticipantResponse,
    ParticipantStatusUpdate,
    PostCreate,
    PostResponse,
    ProposalCreate,
    ProposalResponse,
    QuestionsResponse,
    VoteToggleResponse,
)
from app.application.use_cases import (
    AddPostInput,
    AddPostUseCase,
    AdvanceCycleStatusInput,
    AdvanceCycleStatusUseCase,
    ArchiveCycleUseCase,
    CreateCycleInput,
    CreateCycleUseCase,
    DeleteMeetingUseCase,
    DeletePostUseCase,
    GetCycleQuestionsInput,
    GetCycleQuestionsUseCase,
    GetCycleRatingSummaryUseCase,
    GetCycleUseCase,
    GetSharedHistoryUseCase,
    JoinCycleUseCase,
    ListCyclesUseCase,
    ListMeetingsUseCase,
    ListParticipantsUseCase,
    ListPostsUseCase,
    ListProposalsUseCase,
    PromoteProposalUseCase,
    ProposeBookInput,
    ProposeBookUseCase,
    ScheduleMeetingInput,
    ScheduleMeetingUseCase,
    SetParticipantStatusUseCase,
    ToggleVoteUseCase,
)
from app.domain.repositories import (
    BibliographicRecordRepository,
    BookClubCycleRepository,
    BookClubMeetingRepository,
    BookClubParticipantRepository,
    BookClubPostRepository,
    BookClubProposalRepository,
    BookClubQuestionSetRepository,
    BookClubVoteRepository,
    BookRatingRepository,
    DiscussionQuestionGenerator,
    OwnedBookRepository,
)
from app.infrastructure.database.session import get_db

router = APIRouter(tags=["book-club"])

# Adult members read and post; children have the Kids space instead.
member_role = require_role("admin", "editor", "viewer")
# Only admins/editors run the club (create cycles, advance status, archive).
manager_role = require_role("admin", "editor")


@router.get(
    "/cycles",
    response_model=list[CycleResponse],
    summary="List book club cycles",
    description="Returns every reading cycle for the current library, newest first (active and archived).",
)
async def list_cycles(
    payload: dict[str, Any] = Depends(member_role),
    cycle_repo: BookClubCycleRepository = Depends(get_book_club_cycle_repository),
) -> list[CycleResponse]:
    library_id = UUID(payload["library_id"])
    cycles = await ListCyclesUseCase(cycle_repo).execute(library_id)
    return [CycleResponse.model_validate(c) for c in cycles]


@router.post(
    "/cycles",
    response_model=CycleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a reading cycle",
    description="Create a book club cycle around a record from the library's catalog.",
    responses={
        403: {"description": "Insufficient role or resource not in this library"},
        404: {"description": "Record or book not found"},
    },
)
async def create_cycle(
    body: CycleCreate,
    payload: dict[str, Any] = Depends(manager_role),
    db: AsyncSession = Depends(get_db),
    cycle_repo: BookClubCycleRepository = Depends(get_book_club_cycle_repository),
    record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
    book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
) -> CycleResponse:
    cycle = await CreateCycleUseCase(cycle_repo, record_repo, book_repo).execute(
        CreateCycleInput(
            library_id=UUID(payload["library_id"]),
            created_by=UUID(payload["sub"]),
            bibliographic_record_id=body.bibliographic_record_id,
            title=body.title,
            owned_book_id=body.owned_book_id,
            reading_start=body.reading_start,
            reading_end=body.reading_end,
        )
    )
    await db.commit()
    return CycleResponse.model_validate(cycle)


@router.get(
    "/cycles/{cycle_id}",
    response_model=CycleResponse,
    summary="Get a reading cycle",
    responses={404: {"description": "Cycle not found"}},
)
async def get_cycle(
    cycle_id: UUID,
    payload: dict[str, Any] = Depends(member_role),
    cycle_repo: BookClubCycleRepository = Depends(get_book_club_cycle_repository),
) -> CycleResponse:
    cycle = await GetCycleUseCase(cycle_repo).execute(cycle_id, UUID(payload["library_id"]))
    return CycleResponse.model_validate(cycle)


@router.post(
    "/cycles/{cycle_id}/status",
    response_model=CycleResponse,
    summary="Advance a cycle's status",
    description="Move a cycle forward through reading, discussion. Illegal transitions are rejected.",
    responses={
        403: {"description": "Insufficient role or cycle not in this library"},
        404: {"description": "Cycle not found"},
        409: {"description": "Illegal status transition"},
    },
)
async def advance_cycle_status(
    cycle_id: UUID,
    body: CycleAdvance,
    payload: dict[str, Any] = Depends(manager_role),
    db: AsyncSession = Depends(get_db),
    cycle_repo: BookClubCycleRepository = Depends(get_book_club_cycle_repository),
) -> CycleResponse:
    cycle = await AdvanceCycleStatusUseCase(cycle_repo).execute(
        AdvanceCycleStatusInput(
            cycle_id=cycle_id,
            library_id=UUID(payload["library_id"]),
            target_status=body.target_status,
        )
    )
    await db.commit()
    return CycleResponse.model_validate(cycle)


@router.post(
    "/cycles/{cycle_id}/archive",
    response_model=CycleResponse,
    summary="Archive a cycle",
    description="Close a cycle and move it into the shared reading history.",
    responses={
        403: {"description": "Insufficient role or cycle not in this library"},
        404: {"description": "Cycle not found"},
    },
)
async def archive_cycle(
    cycle_id: UUID,
    payload: dict[str, Any] = Depends(manager_role),
    db: AsyncSession = Depends(get_db),
    cycle_repo: BookClubCycleRepository = Depends(get_book_club_cycle_repository),
) -> CycleResponse:
    cycle = await ArchiveCycleUseCase(cycle_repo).execute(cycle_id, UUID(payload["library_id"]))
    await db.commit()
    return CycleResponse.model_validate(cycle)


@router.get(
    "/cycles/{cycle_id}/posts",
    response_model=list[PostResponse],
    summary="List discussion posts",
    description="Returns the discussion thread for a cycle, oldest first.",
    responses={404: {"description": "Cycle not found"}},
)
async def list_posts(
    cycle_id: UUID,
    payload: dict[str, Any] = Depends(member_role),
    cycle_repo: BookClubCycleRepository = Depends(get_book_club_cycle_repository),
    post_repo: BookClubPostRepository = Depends(get_book_club_post_repository),
) -> list[PostResponse]:
    posts = await ListPostsUseCase(cycle_repo, post_repo).execute(
        cycle_id, UUID(payload["library_id"])
    )
    return [PostResponse.model_validate(p) for p in posts]


@router.post(
    "/cycles/{cycle_id}/posts",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Post to the discussion",
    responses={
        403: {"description": "Cycle not in this library"},
        404: {"description": "Cycle or parent post not found"},
        409: {"description": "Parent post belongs to a different cycle"},
    },
)
async def add_post(
    cycle_id: UUID,
    body: PostCreate,
    payload: dict[str, Any] = Depends(member_role),
    db: AsyncSession = Depends(get_db),
    cycle_repo: BookClubCycleRepository = Depends(get_book_club_cycle_repository),
    post_repo: BookClubPostRepository = Depends(get_book_club_post_repository),
) -> PostResponse:
    post = await AddPostUseCase(cycle_repo, post_repo).execute(
        AddPostInput(
            cycle_id=cycle_id,
            library_id=UUID(payload["library_id"]),
            user_id=UUID(payload["sub"]),
            body=body.body,
            parent_post_id=body.parent_post_id,
            is_spoiler=body.is_spoiler,
        )
    )
    await db.commit()
    return PostResponse.model_validate(post)


@router.delete(
    "/posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a discussion post",
    description="Delete your own post. Admins may delete any post in their library.",
    responses={
        403: {"description": "Cannot delete another user's post, or post not in this library"},
        404: {"description": "Post not found"},
    },
)
async def delete_post(
    post_id: UUID,
    payload: dict[str, Any] = Depends(member_role),
    db: AsyncSession = Depends(get_db),
    cycle_repo: BookClubCycleRepository = Depends(get_book_club_cycle_repository),
    post_repo: BookClubPostRepository = Depends(get_book_club_post_repository),
) -> None:
    await DeletePostUseCase(cycle_repo, post_repo).execute(
        post_id=post_id,
        library_id=UUID(payload["library_id"]),
        user_id=UUID(payload["sub"]),
        is_admin=payload.get("role") == "admin",
    )
    await db.commit()


# ----- Shared reading history (CLUB-03) -----


@router.get(
    "/history",
    response_model=list[HistoryEntryResponse],
    summary="Shared reading history",
    description="Archived cycles with participant counts and the group's average rating.",
)
async def get_history(
    payload: dict[str, Any] = Depends(member_role),
    cycle_repo: BookClubCycleRepository = Depends(get_book_club_cycle_repository),
    participant_repo: BookClubParticipantRepository = Depends(get_book_club_participant_repository),
    rating_repo: BookRatingRepository = Depends(get_book_rating_repository),
    book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
) -> list[HistoryEntryResponse]:
    entries = await GetSharedHistoryUseCase(
        cycle_repo, participant_repo, rating_repo, book_repo
    ).execute(UUID(payload["library_id"]))
    return [
        HistoryEntryResponse(
            cycle=CycleResponse.model_validate(e.cycle),
            participant_count=e.participant_count,
            average_rating=e.average_rating,
        )
        for e in entries
    ]


# ----- Proposals and voting (CLUB-06) -----


@router.get(
    "/proposals",
    response_model=list[ProposalResponse],
    summary="List book proposals",
    description="Candidate books for the next cycle, with vote counts.",
)
async def list_proposals(
    payload: dict[str, Any] = Depends(member_role),
    proposal_repo: BookClubProposalRepository = Depends(get_book_club_proposal_repository),
    vote_repo: BookClubVoteRepository = Depends(get_book_club_vote_repository),
) -> list[ProposalResponse]:
    items = await ListProposalsUseCase(proposal_repo, vote_repo).execute(
        UUID(payload["library_id"]), UUID(payload["sub"])
    )
    return [
        ProposalResponse(
            id=i.proposal.id,
            bibliographic_record_id=i.proposal.bibliographic_record_id,
            proposed_by=i.proposal.proposed_by,
            note=i.proposal.note,
            created_at=i.proposal.created_at,
            vote_count=i.vote_count,
            voted_by_me=i.voted_by_me,
        )
        for i in items
    ]


@router.post(
    "/proposals",
    response_model=ProposalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Propose a book",
    responses={
        403: {"description": "Record not in this library"},
        404: {"description": "Record not found"},
    },
)
async def propose_book(
    body: ProposalCreate,
    payload: dict[str, Any] = Depends(member_role),
    db: AsyncSession = Depends(get_db),
    proposal_repo: BookClubProposalRepository = Depends(get_book_club_proposal_repository),
    record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
) -> ProposalResponse:
    proposal = await ProposeBookUseCase(proposal_repo, record_repo).execute(
        ProposeBookInput(
            library_id=UUID(payload["library_id"]),
            proposed_by=UUID(payload["sub"]),
            bibliographic_record_id=body.bibliographic_record_id,
            note=body.note,
        )
    )
    await db.commit()
    return ProposalResponse(
        id=proposal.id,
        bibliographic_record_id=proposal.bibliographic_record_id,
        proposed_by=proposal.proposed_by,
        note=proposal.note,
        created_at=proposal.created_at,
        vote_count=0,
        voted_by_me=False,
    )


@router.post(
    "/proposals/{proposal_id}/vote",
    response_model=VoteToggleResponse,
    summary="Toggle your vote for a proposal",
    responses={
        403: {"description": "Proposal not in this library"},
        404: {"description": "Proposal not found"},
    },
)
async def toggle_vote(
    proposal_id: UUID,
    payload: dict[str, Any] = Depends(member_role),
    db: AsyncSession = Depends(get_db),
    proposal_repo: BookClubProposalRepository = Depends(get_book_club_proposal_repository),
    vote_repo: BookClubVoteRepository = Depends(get_book_club_vote_repository),
) -> VoteToggleResponse:
    voted = await ToggleVoteUseCase(proposal_repo, vote_repo).execute(
        proposal_id, UUID(payload["library_id"]), UUID(payload["sub"])
    )
    await db.commit()
    return VoteToggleResponse(voted=voted)


@router.post(
    "/proposals/{proposal_id}/promote",
    response_model=CycleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Promote a proposal to a cycle",
    description="Turn the winning proposal into an active reading cycle and clear the proposal pool.",
    responses={
        403: {"description": "Insufficient role or proposal not in this library"},
        404: {"description": "Proposal not found"},
    },
)
async def promote_proposal(
    proposal_id: UUID,
    payload: dict[str, Any] = Depends(manager_role),
    db: AsyncSession = Depends(get_db),
    proposal_repo: BookClubProposalRepository = Depends(get_book_club_proposal_repository),
    cycle_repo: BookClubCycleRepository = Depends(get_book_club_cycle_repository),
    record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
) -> CycleResponse:
    cycle = await PromoteProposalUseCase(proposal_repo, cycle_repo, record_repo).execute(
        proposal_id, UUID(payload["library_id"]), UUID(payload["sub"])
    )
    await db.commit()
    return CycleResponse.model_validate(cycle)


# ----- Participation (CLUB-04) -----


@router.get(
    "/cycles/{cycle_id}/participants",
    response_model=list[ParticipantResponse],
    summary="List cycle participants",
    responses={404: {"description": "Cycle not found"}},
)
async def list_participants(
    cycle_id: UUID,
    payload: dict[str, Any] = Depends(member_role),
    cycle_repo: BookClubCycleRepository = Depends(get_book_club_cycle_repository),
    participant_repo: BookClubParticipantRepository = Depends(get_book_club_participant_repository),
) -> list[ParticipantResponse]:
    items = await ListParticipantsUseCase(cycle_repo, participant_repo).execute(
        cycle_id, UUID(payload["library_id"])
    )
    return [ParticipantResponse.model_validate(p) for p in items]


@router.post(
    "/cycles/{cycle_id}/join",
    response_model=ParticipantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Join a cycle",
    responses={404: {"description": "Cycle not found"}},
)
async def join_cycle(
    cycle_id: UUID,
    payload: dict[str, Any] = Depends(member_role),
    db: AsyncSession = Depends(get_db),
    cycle_repo: BookClubCycleRepository = Depends(get_book_club_cycle_repository),
    participant_repo: BookClubParticipantRepository = Depends(get_book_club_participant_repository),
) -> ParticipantResponse:
    participant = await JoinCycleUseCase(cycle_repo, participant_repo).execute(
        cycle_id, UUID(payload["library_id"]), UUID(payload["sub"])
    )
    await db.commit()
    return ParticipantResponse.model_validate(participant)


@router.post(
    "/cycles/{cycle_id}/participants/me/status",
    response_model=ParticipantResponse,
    summary="Update your participation status",
    responses={404: {"description": "Cycle not found or you have not joined"}},
)
async def set_participant_status(
    cycle_id: UUID,
    body: ParticipantStatusUpdate,
    payload: dict[str, Any] = Depends(member_role),
    db: AsyncSession = Depends(get_db),
    cycle_repo: BookClubCycleRepository = Depends(get_book_club_cycle_repository),
    participant_repo: BookClubParticipantRepository = Depends(get_book_club_participant_repository),
) -> ParticipantResponse:
    participant = await SetParticipantStatusUseCase(cycle_repo, participant_repo).execute(
        cycle_id, UUID(payload["library_id"]), UUID(payload["sub"]), body.status
    )
    await db.commit()
    return ParticipantResponse.model_validate(participant)


# ----- Meetings (CLUB-07) -----


@router.get(
    "/cycles/{cycle_id}/meetings",
    response_model=list[MeetingResponse],
    summary="List cycle meetings",
    responses={404: {"description": "Cycle not found"}},
)
async def list_meetings(
    cycle_id: UUID,
    payload: dict[str, Any] = Depends(member_role),
    cycle_repo: BookClubCycleRepository = Depends(get_book_club_cycle_repository),
    meeting_repo: BookClubMeetingRepository = Depends(get_book_club_meeting_repository),
) -> list[MeetingResponse]:
    items = await ListMeetingsUseCase(cycle_repo, meeting_repo).execute(
        cycle_id, UUID(payload["library_id"])
    )
    return [MeetingResponse.model_validate(m) for m in items]


@router.post(
    "/cycles/{cycle_id}/meetings",
    response_model=MeetingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule a meeting",
    responses={
        403: {"description": "Insufficient role or cycle not in this library"},
        404: {"description": "Cycle not found"},
    },
)
async def schedule_meeting(
    cycle_id: UUID,
    body: MeetingCreate,
    payload: dict[str, Any] = Depends(manager_role),
    db: AsyncSession = Depends(get_db),
    cycle_repo: BookClubCycleRepository = Depends(get_book_club_cycle_repository),
    meeting_repo: BookClubMeetingRepository = Depends(get_book_club_meeting_repository),
) -> MeetingResponse:
    meeting = await ScheduleMeetingUseCase(cycle_repo, meeting_repo).execute(
        ScheduleMeetingInput(
            cycle_id=cycle_id,
            library_id=UUID(payload["library_id"]),
            created_by=UUID(payload["sub"]),
            scheduled_at=body.scheduled_at,
            note=body.note,
        )
    )
    await db.commit()
    return MeetingResponse.model_validate(meeting)


@router.delete(
    "/meetings/{meeting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a meeting",
    responses={
        403: {"description": "Insufficient role or meeting not in this library"},
        404: {"description": "Meeting not found"},
    },
)
async def delete_meeting(
    meeting_id: UUID,
    payload: dict[str, Any] = Depends(manager_role),
    db: AsyncSession = Depends(get_db),
    cycle_repo: BookClubCycleRepository = Depends(get_book_club_cycle_repository),
    meeting_repo: BookClubMeetingRepository = Depends(get_book_club_meeting_repository),
) -> None:
    await DeleteMeetingUseCase(cycle_repo, meeting_repo).execute(
        meeting_id, UUID(payload["library_id"])
    )
    await db.commit()


# ----- Cycle rating summary (CLUB-05) -----


@router.get(
    "/cycles/{cycle_id}/rating",
    response_model=CycleRatingResponse,
    summary="Cycle rating summary",
    description="Average of members' ratings on the cycle's book (reuses BookRating).",
    responses={404: {"description": "Cycle not found"}},
)
async def get_cycle_rating(
    cycle_id: UUID,
    payload: dict[str, Any] = Depends(member_role),
    cycle_repo: BookClubCycleRepository = Depends(get_book_club_cycle_repository),
    rating_repo: BookRatingRepository = Depends(get_book_rating_repository),
) -> CycleRatingResponse:
    summary = await GetCycleRatingSummaryUseCase(cycle_repo, rating_repo).execute(
        cycle_id, UUID(payload["library_id"])
    )
    return CycleRatingResponse(average=summary.average, total=summary.total)


# ----- AI discussion prompts (CLUB-08, optional) -----


@router.get(
    "/cycles/{cycle_id}/questions",
    response_model=QuestionsResponse,
    summary="AI discussion prompts",
    description="Get-or-generate discussion prompts for the cycle's book. Empty when AI is off.",
    responses={404: {"description": "Cycle not found"}},
)
async def get_cycle_questions(
    cycle_id: UUID,
    lang: str | None = None,
    payload: dict[str, Any] = Depends(member_role),
    db: AsyncSession = Depends(get_db),
    cycle_repo: BookClubCycleRepository = Depends(get_book_club_cycle_repository),
    record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
    question_set_repo: BookClubQuestionSetRepository = Depends(get_book_club_question_set_repository),
    generator: DiscussionQuestionGenerator = Depends(get_discussion_generator),
) -> QuestionsResponse:
    # The caller's current UI language wins over the JWT's language claim: a
    # member who switched language in-session must get prompts in that language.
    reader_language = lang or payload.get("language")
    questions = await GetCycleQuestionsUseCase(
        cycle_repo, record_repo, question_set_repo, generator
    ).execute(
        GetCycleQuestionsInput(
            cycle_id=cycle_id,
            library_id=UUID(payload["library_id"]),
            reader_language=reader_language,
        )
    )
    # A newly generated set is written inside the use case; commit it.
    await db.commit()
    return QuestionsResponse(questions=questions)
