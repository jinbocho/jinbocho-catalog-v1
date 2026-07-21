from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
	get_bibliographic_record_repository,
	get_book_read_repository,
	get_current_user_payload,
	get_discussion_generator,
	get_discussion_question_set_repository,
	get_family_challenge_repository,
	get_journal_entry_repository,
	get_mystery_pick_repository,
	get_owned_book_repository,
	get_quiz_attempt_repository,
	get_quiz_generator,
	get_quiz_question_repository,
	get_reading_path_repository,
	get_reading_session_repository,
	require_child,
	require_child_or_parent,
	require_parent,
)
from app.api.v1.schemas.kids_schemas import (
	DiscussionQuestionsResponse,
	FamilyChallengeCreate,
	FamilyChallengeProgressResponse,
	FamilyChallengeResponse,
	JournalEntryCreate,
	JournalEntryResponse,
	MysteryPickCreate,
	MysteryPickResponse,
	QuizAnswerReviewResponse,
	QuizAttemptDetailResponse,
	QuizAttemptResponse,
	QuizGenerateRequest,
	QuizQuestionAuthorResponse,
	QuizQuestionCreate,
	QuizQuestionResponse,
	QuizSubmitRequest,
	ReadingPathCreate,
	ReadingPathResponse,
	ReadingSessionCreate,
	ReadingSessionResponse,
)
from app.application.services import QuizScoringService, age_band_for_birth_year
from app.application.use_cases import (
	AcceptMysteryPickInput,
	AcceptMysteryPickUseCase,
	CreateFamilyChallengeInput,
	CreateFamilyChallengeUseCase,
	CreateJournalEntryInput,
	CreateJournalEntryUseCase,
	CreateManualQuizQuestionInput,
	CreateManualQuizQuestionUseCase,
	CreateMysteryPickInput,
	CreateMysteryPickUseCase,
	CreateReadingPathInput,
	CreateReadingPathUseCase,
	DeleteFamilyChallengeInput,
	DeleteFamilyChallengeUseCase,
	DeleteReadingPathInput,
	DeleteReadingPathUseCase,
	GenerateQuizQuestionsInput,
	GenerateQuizQuestionsUseCase,
	GetDiscussionQuestionsInput,
	GetDiscussionQuestionsUseCase,
	GetFamilyChallengeProgressInput,
	GetFamilyChallengeProgressUseCase,
	GetQuizAttemptDetailInput,
	GetQuizAttemptDetailUseCase,
	ListFamilyChallengesInput,
	ListFamilyChallengesUseCase,
	ListJournalEntriesInput,
	ListJournalEntriesUseCase,
	ListMysteryPicksInput,
	ListMysteryPicksUseCase,
	ListQuizAttemptsInput,
	ListQuizAttemptsUseCase,
	ListQuizQuestionsInput,
	ListQuizQuestionsUseCase,
	ListReadingPathsInput,
	ListReadingPathsUseCase,
	ListReadingSessionsInput,
	ListReadingSessionsUseCase,
	LogReadingSessionInput,
	LogReadingSessionUseCase,
	SubmitQuizAttemptInput,
	SubmitQuizAttemptUseCase,
)
from app.domain.entities import ChallengeMetric, JournalPromptKind, MysteryPick, ReadingSessionMode
from app.domain.repositories import (
	BibliographicRecordRepository,
	BookReadRepository,
	DiscussionQuestionGenerator,
	DiscussionQuestionSetRepository,
	FamilyChallengeRepository,
	JournalEntryRepository,
	MysteryPickRepository,
	OwnedBookRepository,
	QuizAttemptRepository,
	QuizGenerator,
	QuizQuestionRepository,
	ReadingPathRepository,
	ReadingSessionRepository,
)
from app.infrastructure.database.session import get_db

router = APIRouter(tags=["kids"])


@router.post(
	"/sessions",
	response_model=ReadingSessionResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Log a reading session (kids mode only)",
	description="A child logs their own minutes/pages (mode='independent'), or a parent logs a "
	"shared reading session on behalf of a 0-5 child who has no autonomous reading yet "
	"(mode='together', KID-02). Requires kids mode enabled for the library.",
	responses={
		403: {"description": "Kids mode disabled, book belongs to another library, or role mismatch for the mode"},
		404: {"description": "Book not found"},
	},
)
async def log_reading_session(
	body: ReadingSessionCreate,
	payload: dict[str, Any] = Depends(require_child_or_parent),
	db: AsyncSession = Depends(get_db),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	session_repo: ReadingSessionRepository = Depends(get_reading_session_repository),
) -> ReadingSessionResponse:
	library_id = UUID(payload["library_id"])
	requester_id = UUID(payload["sub"])
	session = await LogReadingSessionUseCase(book_repo, session_repo).execute(
		LogReadingSessionInput(
			owned_book_id=body.owned_book_id,
			library_id=library_id,
			target_user_id=body.target_user_id or requester_id,
			requester_user_id=requester_id,
			requester_role=str(payload.get("role")),
			kids_mode_enabled=bool(payload.get("kids_mode_enabled", False)),
			minutes=body.minutes,
			pages=body.pages,
			session_date=body.session_date,
			mode=ReadingSessionMode(body.mode),
		)
	)
	await db.commit()
	return ReadingSessionResponse.model_validate(session)


@router.get(
	"/sessions",
	response_model=list[ReadingSessionResponse],
	summary="List reading sessions for a user (kids mode only)",
	description="A child sees only their own sessions; an admin/editor can view any member's, "
	"for the read-only parent dashboard.",
	responses={403: {"description": "Kids mode disabled, or not authorized to view this user's sessions"}},
)
async def list_reading_sessions(
	user_id: UUID,
	payload: dict[str, Any] = Depends(get_current_user_payload),
	session_repo: ReadingSessionRepository = Depends(get_reading_session_repository),
) -> list[ReadingSessionResponse]:
	library_id = UUID(payload["library_id"])
	sessions = await ListReadingSessionsUseCase(session_repo).execute(
		ListReadingSessionsInput(
			target_user_id=user_id,
			library_id=library_id,
			requester_user_id=UUID(payload["sub"]),
			requester_role=str(payload.get("role")),
			kids_mode_enabled=bool(payload.get("kids_mode_enabled", False)),
		)
	)
	return [ReadingSessionResponse.model_validate(s) for s in sessions]


@router.post(
	"/books/{owned_book_id}/quiz/generate",
	response_model=list[QuizQuestionResponse],
	summary="Get or generate the comprehension quiz for a book (kids mode only)",
	description="If the book already has questions (AI or manual) and no extra_context is given, "
	"returns them unchanged. Otherwise (no questions yet, or extra_context supplied) asks "
	"ai-service to generate more from the book's metadata/incipit/extra_context — if the AI "
	"module is disabled or the call fails, returns whatever already existed rather than erroring, "
	"so the caller can fall back to a manual quiz a parent adds separately. The child can self-serve "
	"this, or a parent (admin/editor) can prepare/review it ahead of time — either role works.",
	responses={
		403: {"description": "Kids mode disabled, or book belongs to another library"},
		404: {"description": "Book not found"},
	},
)
async def generate_quiz(
	owned_book_id: UUID,
	body: QuizGenerateRequest,
	payload: dict[str, Any] = Depends(require_child_or_parent),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
	question_repo: QuizQuestionRepository = Depends(get_quiz_question_repository),
	quiz_generator: QuizGenerator = Depends(get_quiz_generator),
	db: AsyncSession = Depends(get_db),
) -> list[QuizQuestionResponse]:
	library_id = UUID(payload["library_id"])
	questions = await GenerateQuizQuestionsUseCase(book_repo, record_repo, question_repo, quiz_generator).execute(
		GenerateQuizQuestionsInput(
			owned_book_id=owned_book_id,
			library_id=library_id,
			kids_mode_enabled=bool(payload.get("kids_mode_enabled", False)),
			num_questions=body.num_questions,
			extra_context=body.extra_context,
			reader_age_band=age_band_for_birth_year(payload.get("birth_year")),
			reader_language=payload.get("language"),
		)
	)
	await db.commit()
	return [QuizQuestionResponse.model_validate(q) for q in questions]


@router.get(
	"/books/{owned_book_id}/quiz",
	response_model=list[QuizQuestionResponse],
	summary="List the comprehension quiz for a book (kids mode only)",
	description="Read-only, no generation — use POST .../generate first if this returns empty.",
	responses={
		403: {"description": "Kids mode disabled, or book belongs to another library"},
		404: {"description": "Book not found"},
	},
)
async def list_quiz_questions(
	owned_book_id: UUID,
	payload: dict[str, Any] = Depends(get_current_user_payload),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	question_repo: QuizQuestionRepository = Depends(get_quiz_question_repository),
) -> list[QuizQuestionResponse]:
	library_id = UUID(payload["library_id"])
	questions = await ListQuizQuestionsUseCase(book_repo, question_repo).execute(
		ListQuizQuestionsInput(
			owned_book_id=owned_book_id,
			library_id=library_id,
			kids_mode_enabled=bool(payload.get("kids_mode_enabled", False)),
		)
	)
	return [QuizQuestionResponse.model_validate(q) for q in questions]


@router.post(
	"/books/{owned_book_id}/quiz/questions",
	response_model=QuizQuestionAuthorResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Author a manual quiz question for a book (kids mode only)",
	description="A parent who actually read the book writes a richer question than AI can. "
	"Requires kids mode enabled and admin/editor role.",
	responses={
		403: {"description": "Kids mode disabled, or book belongs to another library"},
		404: {"description": "Book not found"},
	},
)
async def create_manual_quiz_question(
	owned_book_id: UUID,
	body: QuizQuestionCreate,
	payload: dict[str, Any] = Depends(require_parent),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	question_repo: QuizQuestionRepository = Depends(get_quiz_question_repository),
	db: AsyncSession = Depends(get_db),
) -> QuizQuestionAuthorResponse:
	library_id = UUID(payload["library_id"])
	author_user_id = UUID(payload["sub"])
	question = await CreateManualQuizQuestionUseCase(book_repo, question_repo).execute(
		CreateManualQuizQuestionInput(
			owned_book_id=owned_book_id,
			library_id=library_id,
			author_user_id=author_user_id,
			prompt=body.prompt,
			choices=body.choices,
			correct_index=body.correct_index,
			kids_mode_enabled=bool(payload.get("kids_mode_enabled", False)),
		)
	)
	await db.commit()
	return QuizQuestionAuthorResponse.model_validate(question)


@router.post(
	"/books/{owned_book_id}/quiz/attempts",
	response_model=QuizAttemptResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Submit a quiz attempt (kids mode only)",
	description="Self-service: a child submits their answers and gets a score back. Requires the CHILD role.",
	responses={
		403: {"description": "Kids mode disabled, or book belongs to another library"},
		404: {"description": "One or more questions not found for this book"},
	},
)
async def submit_quiz_attempt(
	owned_book_id: UUID,
	body: QuizSubmitRequest,
	payload: dict[str, Any] = Depends(require_child),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	question_repo: QuizQuestionRepository = Depends(get_quiz_question_repository),
	attempt_repo: QuizAttemptRepository = Depends(get_quiz_attempt_repository),
	db: AsyncSession = Depends(get_db),
) -> QuizAttemptResponse:
	library_id = UUID(payload["library_id"])
	user_id = UUID(payload["sub"])
	attempt = await SubmitQuizAttemptUseCase(book_repo, question_repo, attempt_repo, QuizScoringService()).execute(
		SubmitQuizAttemptInput(
			owned_book_id=owned_book_id,
			library_id=library_id,
			user_id=user_id,
			kids_mode_enabled=bool(payload.get("kids_mode_enabled", False)),
			answers=body.answers,
		)
	)
	await db.commit()
	return QuizAttemptResponse.model_validate(attempt)


@router.get(
	"/attempts",
	response_model=list[QuizAttemptResponse],
	summary="List quiz attempts for a user (kids mode only)",
	description="A child sees only their own attempts; an admin/editor can view any member's, "
	"for the read-only parent dashboard.",
	responses={403: {"description": "Kids mode disabled, or not authorized to view this user's attempts"}},
)
async def list_quiz_attempts(
	user_id: UUID,
	payload: dict[str, Any] = Depends(get_current_user_payload),
	attempt_repo: QuizAttemptRepository = Depends(get_quiz_attempt_repository),
) -> list[QuizAttemptResponse]:
	library_id = UUID(payload["library_id"])
	attempts = await ListQuizAttemptsUseCase(attempt_repo).execute(
		ListQuizAttemptsInput(
			target_user_id=user_id,
			library_id=library_id,
			requester_user_id=UUID(payload["sub"]),
			requester_role=str(payload.get("role")),
			kids_mode_enabled=bool(payload.get("kids_mode_enabled", False)),
		)
	)
	return [QuizAttemptResponse.model_validate(a) for a in attempts]


@router.get(
	"/attempts/{attempt_id}",
	response_model=QuizAttemptDetailResponse,
	summary="Get a quiz attempt with per-question answer review (kids mode only)",
	description="Powers the parent dashboard's \"view answers\" modal — each question's prompt, "
	"choices, correct answer, and what the child actually selected. A child sees only their own "
	"attempts; an admin/editor can view any member's.",
	responses={
		403: {"description": "Kids mode disabled, or not authorized to view this attempt"},
		404: {"description": "Attempt or book not found"},
	},
)
async def get_quiz_attempt_detail(
	attempt_id: UUID,
	payload: dict[str, Any] = Depends(get_current_user_payload),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	question_repo: QuizQuestionRepository = Depends(get_quiz_question_repository),
	attempt_repo: QuizAttemptRepository = Depends(get_quiz_attempt_repository),
) -> QuizAttemptDetailResponse:
	library_id = UUID(payload["library_id"])
	detail = await GetQuizAttemptDetailUseCase(book_repo, question_repo, attempt_repo).execute(
		GetQuizAttemptDetailInput(
			attempt_id=attempt_id,
			library_id=library_id,
			requester_user_id=UUID(payload["sub"]),
			requester_role=str(payload.get("role")),
			kids_mode_enabled=bool(payload.get("kids_mode_enabled", False)),
		)
	)
	return QuizAttemptDetailResponse(
		id=detail.attempt.id,
		owned_book_id=detail.attempt.owned_book_id,
		user_id=detail.attempt.user_id,
		score=detail.attempt.score,
		total=detail.attempt.total,
		passed=detail.attempt.passed,
		created_at=detail.attempt.created_at,
		answers=[
			QuizAnswerReviewResponse(
				question_id=a.question_id,
				prompt=a.prompt,
				choices=a.choices,
				correct_index=a.correct_index,
				selected_index=a.selected_index,
				is_correct=a.is_correct,
			)
			for a in detail.answers
		],
	)


@router.get(
	"/books/{owned_book_id}/discussion",
	response_model=DiscussionQuestionsResponse,
	summary="Get or generate dinner-table conversation questions for a book (kids mode only)",
	description="KID-04: AI-generated conversation starters for a parent, not a comprehension "
	"check — no right answer, never shown to the child. Cached one set per book after the first "
	"generation. Parent-only (unlike the quiz, this isn't meant for the child to see).",
	responses={
		403: {"description": "Kids mode disabled, or book belongs to another library"},
		404: {"description": "Book not found"},
	},
)
async def get_discussion_questions(
	owned_book_id: UUID,
	# The caller is the parent, not the reading child — their own birth_year
	# claim is irrelevant here. The FE already has the child's birth_year
	# from the member roster (KID-01) and computes the band client-side.
	reader_age_band: str | None = None,
	payload: dict[str, Any] = Depends(require_parent),
	db: AsyncSession = Depends(get_db),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
	question_set_repo: DiscussionQuestionSetRepository = Depends(get_discussion_question_set_repository),
	generator: DiscussionQuestionGenerator = Depends(get_discussion_generator),
) -> DiscussionQuestionsResponse:
	library_id = UUID(payload["library_id"])
	questions = await GetDiscussionQuestionsUseCase(book_repo, record_repo, question_set_repo, generator).execute(
		GetDiscussionQuestionsInput(
			owned_book_id=owned_book_id,
			library_id=library_id,
			kids_mode_enabled=bool(payload.get("kids_mode_enabled", False)),
			reader_age_band=reader_age_band,
			reader_language=payload.get("language"),
		)
	)
	await db.commit()
	return DiscussionQuestionsResponse(questions=questions)


@router.post(
	"/journal",
	response_model=JournalEntryResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Write a journal entry for a book (kids mode only)",
	description="KID-03: self-service, a child writes their own free-text/emoji/retelling response "
	"about a book — never a comprehension check, no scoring. Requires kids mode enabled and the "
	"CHILD role.",
	responses={
		403: {"description": "Kids mode disabled, or book belongs to another library"},
		404: {"description": "Book not found"},
	},
)
async def create_journal_entry(
	body: JournalEntryCreate,
	payload: dict[str, Any] = Depends(require_child),
	db: AsyncSession = Depends(get_db),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	entry_repo: JournalEntryRepository = Depends(get_journal_entry_repository),
) -> JournalEntryResponse:
	library_id = UUID(payload["library_id"])
	user_id = UUID(payload["sub"])
	entry = await CreateJournalEntryUseCase(book_repo, entry_repo).execute(
		CreateJournalEntryInput(
			owned_book_id=body.owned_book_id,
			library_id=library_id,
			user_id=user_id,
			kids_mode_enabled=bool(payload.get("kids_mode_enabled", False)),
			text=body.text,
			prompt_kind=JournalPromptKind(body.prompt_kind),
			emoji=body.emoji,
			session_id=body.session_id,
		)
	)
	await db.commit()
	return JournalEntryResponse.model_validate(entry)


@router.get(
	"/journal",
	response_model=list[JournalEntryResponse],
	summary="List journal entries for a user (kids mode only)",
	description="A child sees only their own entries; an admin/editor can view any member's, "
	"read-only, for the parent dashboard feed.",
	responses={403: {"description": "Kids mode disabled, or not authorized to view this user's entries"}},
)
async def list_journal_entries(
	user_id: UUID,
	payload: dict[str, Any] = Depends(get_current_user_payload),
	entry_repo: JournalEntryRepository = Depends(get_journal_entry_repository),
) -> list[JournalEntryResponse]:
	library_id = UUID(payload["library_id"])
	entries = await ListJournalEntriesUseCase(entry_repo).execute(
		ListJournalEntriesInput(
			target_user_id=user_id,
			library_id=library_id,
			requester_user_id=UUID(payload["sub"]),
			requester_role=str(payload.get("role")),
			kids_mode_enabled=bool(payload.get("kids_mode_enabled", False)),
		)
	)
	return [JournalEntryResponse.model_validate(e) for e in entries]


@router.post(
	"/paths",
	response_model=ReadingPathResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Create a reading path (kids mode only)",
	description="KID-06: a parent curates an ordered sequence of books from the family's own "
	"catalog around something the child likes. Completion is derived client-side from BookRead, "
	"not stored here. Requires kids mode enabled and admin/editor role.",
	responses={403: {"description": "Kids mode disabled"}},
)
async def create_reading_path(
	body: ReadingPathCreate,
	payload: dict[str, Any] = Depends(require_parent),
	db: AsyncSession = Depends(get_db),
	path_repo: ReadingPathRepository = Depends(get_reading_path_repository),
) -> ReadingPathResponse:
	library_id = UUID(payload["library_id"])
	path = await CreateReadingPathUseCase(path_repo).execute(
		CreateReadingPathInput(
			library_id=library_id,
			created_by=UUID(payload["sub"]),
			kids_mode_enabled=bool(payload.get("kids_mode_enabled", False)),
			title=body.title,
			book_ids=body.book_ids,
			description=body.description,
			target_band=body.target_band,
		)
	)
	await db.commit()
	return ReadingPathResponse.model_validate(path)


@router.get(
	"/paths",
	response_model=list[ReadingPathResponse],
	summary="List reading paths for the library (kids mode only)",
	description="Open to any authenticated library member — a child sees their reading paths, "
	"a parent manages them.",
	responses={403: {"description": "Kids mode disabled"}},
)
async def list_reading_paths(
	payload: dict[str, Any] = Depends(get_current_user_payload),
	path_repo: ReadingPathRepository = Depends(get_reading_path_repository),
) -> list[ReadingPathResponse]:
	library_id = UUID(payload["library_id"])
	paths = await ListReadingPathsUseCase(path_repo).execute(
		ListReadingPathsInput(library_id=library_id, kids_mode_enabled=bool(payload.get("kids_mode_enabled", False)))
	)
	return [ReadingPathResponse.model_validate(p) for p in paths]


@router.delete(
	"/paths/{path_id}",
	status_code=status.HTTP_204_NO_CONTENT,
	summary="Delete a reading path (kids mode only)",
	responses={
		403: {"description": "Kids mode disabled, or path belongs to another library"},
		404: {"description": "Reading path not found"},
	},
)
async def delete_reading_path(
	path_id: UUID,
	payload: dict[str, Any] = Depends(require_parent),
	db: AsyncSession = Depends(get_db),
	path_repo: ReadingPathRepository = Depends(get_reading_path_repository),
) -> None:
	library_id = UUID(payload["library_id"])
	await DeleteReadingPathUseCase(path_repo).execute(
		DeleteReadingPathInput(
			path_id=path_id, library_id=library_id, kids_mode_enabled=bool(payload.get("kids_mode_enabled", False))
		)
	)
	await db.commit()


def _mystery_pick_response(pick: MysteryPick, requester_role: str) -> MysteryPickResponse:
	# Hide owned_book_id from the child while proposed — that's the whole
	# point of the challenge. A parent always sees it (they picked it).
	is_parent = requester_role in ("admin", "editor")
	hide = pick.status.value == "proposed" and not is_parent
	return MysteryPickResponse(
		id=pick.id,
		owned_book_id=None if hide else pick.owned_book_id,
		child_user_id=pick.child_user_id,
		hint_text=pick.hint_text,
		status=pick.status.value,
		created_at=pick.created_at,
	)


@router.post(
	"/mystery",
	response_model=MysteryPickResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Propose a mystery book to a child (kids mode only)",
	description="KID-07 'libro al buio': a parent picks a book from the catalog and the child sees "
	"only a masked hint (reused from the incipit feature) until they accept. Requires kids mode "
	"enabled and admin/editor role.",
	responses={403: {"description": "Kids mode disabled"}, 404: {"description": "Book not found"}},
)
async def create_mystery_pick(
	body: MysteryPickCreate,
	payload: dict[str, Any] = Depends(require_parent),
	db: AsyncSession = Depends(get_db),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
	pick_repo: MysteryPickRepository = Depends(get_mystery_pick_repository),
) -> MysteryPickResponse:
	library_id = UUID(payload["library_id"])
	pick = await CreateMysteryPickUseCase(book_repo, record_repo, pick_repo).execute(
		CreateMysteryPickInput(
			library_id=library_id,
			owned_book_id=body.owned_book_id,
			child_user_id=body.child_user_id,
			created_by=UUID(payload["sub"]),
			kids_mode_enabled=bool(payload.get("kids_mode_enabled", False)),
		)
	)
	await db.commit()
	return _mystery_pick_response(pick, str(payload.get("role")))


@router.post(
	"/mystery/{pick_id}/accept",
	response_model=MysteryPickResponse,
	summary="Accept a mystery book challenge (kids mode only)",
	description="Only the child the pick was proposed to can accept — accepting reveals the book. "
	"Requires kids mode enabled and the CHILD role.",
	responses={
		403: {"description": "Kids mode disabled, pick belongs to another library, or not this child's pick"},
		404: {"description": "Mystery pick not found"},
	},
)
async def accept_mystery_pick(
	pick_id: UUID,
	payload: dict[str, Any] = Depends(require_child),
	db: AsyncSession = Depends(get_db),
	pick_repo: MysteryPickRepository = Depends(get_mystery_pick_repository),
) -> MysteryPickResponse:
	library_id = UUID(payload["library_id"])
	pick = await AcceptMysteryPickUseCase(pick_repo).execute(
		AcceptMysteryPickInput(
			pick_id=pick_id,
			library_id=library_id,
			requester_user_id=UUID(payload["sub"]),
			kids_mode_enabled=bool(payload.get("kids_mode_enabled", False)),
		)
	)
	await db.commit()
	return _mystery_pick_response(pick, str(payload.get("role")))


@router.get(
	"/mystery",
	response_model=list[MysteryPickResponse],
	summary="List mystery book picks for a child (kids mode only)",
	description="A child sees only their own picks (book hidden while proposed); an admin/editor "
	"can view any child's, always with the book visible.",
	responses={403: {"description": "Kids mode disabled, or not authorized to view this child's picks"}},
)
async def list_mystery_picks(
	child_user_id: UUID,
	payload: dict[str, Any] = Depends(get_current_user_payload),
	pick_repo: MysteryPickRepository = Depends(get_mystery_pick_repository),
) -> list[MysteryPickResponse]:
	library_id = UUID(payload["library_id"])
	picks = await ListMysteryPicksUseCase(pick_repo).execute(
		ListMysteryPicksInput(
			child_user_id=child_user_id,
			library_id=library_id,
			requester_user_id=UUID(payload["sub"]),
			requester_role=str(payload.get("role")),
			kids_mode_enabled=bool(payload.get("kids_mode_enabled", False)),
		)
	)
	role = str(payload.get("role"))
	return [_mystery_pick_response(p, role) for p in picks]


@router.post(
	"/challenges",
	response_model=FamilyChallengeResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Create a family reading challenge (kids mode only)",
	description="KID-08: a single cooperative target the whole library works toward together — "
	"never a per-member breakdown or leaderboard. Requires kids mode enabled and admin/editor role.",
	responses={403: {"description": "Kids mode disabled"}},
)
async def create_family_challenge(
	body: FamilyChallengeCreate,
	payload: dict[str, Any] = Depends(require_parent),
	db: AsyncSession = Depends(get_db),
	challenge_repo: FamilyChallengeRepository = Depends(get_family_challenge_repository),
) -> FamilyChallengeResponse:
	library_id = UUID(payload["library_id"])
	challenge = await CreateFamilyChallengeUseCase(challenge_repo).execute(
		CreateFamilyChallengeInput(
			library_id=library_id,
			created_by=UUID(payload["sub"]),
			kids_mode_enabled=bool(payload.get("kids_mode_enabled", False)),
			title=body.title,
			metric=ChallengeMetric(body.metric),
			target=body.target,
			starts_on=body.starts_on,
			ends_on=body.ends_on,
		)
	)
	await db.commit()
	return FamilyChallengeResponse.model_validate(challenge)


@router.get(
	"/challenges",
	response_model=list[FamilyChallengeResponse],
	summary="List family reading challenges (kids mode only)",
	description="Open to any authenticated library member — everyone sees and works toward the "
	"same shared goal.",
	responses={403: {"description": "Kids mode disabled"}},
)
async def list_family_challenges(
	payload: dict[str, Any] = Depends(get_current_user_payload),
	challenge_repo: FamilyChallengeRepository = Depends(get_family_challenge_repository),
) -> list[FamilyChallengeResponse]:
	library_id = UUID(payload["library_id"])
	challenges = await ListFamilyChallengesUseCase(challenge_repo).execute(
		ListFamilyChallengesInput(
			library_id=library_id, kids_mode_enabled=bool(payload.get("kids_mode_enabled", False))
		)
	)
	return [FamilyChallengeResponse.model_validate(c) for c in challenges]


@router.get(
	"/challenges/{challenge_id}/progress",
	response_model=FamilyChallengeProgressResponse,
	summary="Get cooperative progress toward a family challenge (kids mode only)",
	description="A single number summed across every member of the library within the challenge "
	"window — deliberately never broken down per member.",
	responses={
		403: {"description": "Kids mode disabled, or challenge belongs to another library"},
		404: {"description": "Family challenge not found"},
	},
)
async def get_family_challenge_progress(
	challenge_id: UUID,
	payload: dict[str, Any] = Depends(get_current_user_payload),
	challenge_repo: FamilyChallengeRepository = Depends(get_family_challenge_repository),
	session_repo: ReadingSessionRepository = Depends(get_reading_session_repository),
	read_repo: BookReadRepository = Depends(get_book_read_repository),
) -> FamilyChallengeProgressResponse:
	library_id = UUID(payload["library_id"])
	progress = await GetFamilyChallengeProgressUseCase(challenge_repo, session_repo, read_repo).execute(
		GetFamilyChallengeProgressInput(
			challenge_id=challenge_id,
			library_id=library_id,
			kids_mode_enabled=bool(payload.get("kids_mode_enabled", False)),
		)
	)
	return FamilyChallengeProgressResponse(
		challenge=FamilyChallengeResponse.model_validate(progress.challenge), current=progress.current
	)


@router.delete(
	"/challenges/{challenge_id}",
	status_code=status.HTTP_204_NO_CONTENT,
	summary="Delete a family reading challenge (kids mode only)",
	responses={
		403: {"description": "Kids mode disabled, or challenge belongs to another library"},
		404: {"description": "Family challenge not found"},
	},
)
async def delete_family_challenge(
	challenge_id: UUID,
	payload: dict[str, Any] = Depends(require_parent),
	db: AsyncSession = Depends(get_db),
	challenge_repo: FamilyChallengeRepository = Depends(get_family_challenge_repository),
) -> None:
	library_id = UUID(payload["library_id"])
	await DeleteFamilyChallengeUseCase(challenge_repo).execute(
		DeleteFamilyChallengeInput(
			challenge_id=challenge_id,
			library_id=library_id,
			kids_mode_enabled=bool(payload.get("kids_mode_enabled", False)),
		)
	)
	await db.commit()
