from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
	get_bibliographic_record_repository,
	get_current_user_payload,
	get_owned_book_repository,
	get_quiz_attempt_repository,
	get_quiz_generator,
	get_quiz_question_repository,
	get_reading_session_repository,
	require_child,
	require_child_or_parent,
	require_parent,
)
from app.api.v1.schemas.kids_schemas import (
	QuizAnswerReviewResponse,
	QuizAttemptDetailResponse,
	QuizAttemptResponse,
	QuizGenerateRequest,
	QuizQuestionAuthorResponse,
	QuizQuestionCreate,
	QuizQuestionResponse,
	QuizSubmitRequest,
	ReadingSessionCreate,
	ReadingSessionResponse,
)
from app.application.services import QuizScoringService
from app.application.use_cases import (
	CreateManualQuizQuestionInput,
	CreateManualQuizQuestionUseCase,
	GenerateQuizQuestionsInput,
	GenerateQuizQuestionsUseCase,
	GetQuizAttemptDetailInput,
	GetQuizAttemptDetailUseCase,
	ListQuizAttemptsInput,
	ListQuizAttemptsUseCase,
	ListQuizQuestionsInput,
	ListQuizQuestionsUseCase,
	ListReadingSessionsInput,
	ListReadingSessionsUseCase,
	LogReadingSessionInput,
	LogReadingSessionUseCase,
	SubmitQuizAttemptInput,
	SubmitQuizAttemptUseCase,
)
from app.domain.repositories import (
	BibliographicRecordRepository,
	OwnedBookRepository,
	QuizAttemptRepository,
	QuizGenerator,
	QuizQuestionRepository,
	ReadingSessionRepository,
)
from app.infrastructure.database.session import get_db

router = APIRouter(tags=["kids"])


@router.post(
	"/sessions",
	response_model=ReadingSessionResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Log a reading session (kids mode only)",
	description="Self-service: a child logs their own minutes/pages for a book they have access to. "
	"Requires kids mode enabled for the library and the CHILD role.",
	responses={
		403: {"description": "Kids mode disabled, or book belongs to another library"},
		404: {"description": "Book not found"},
	},
)
async def log_reading_session(
	body: ReadingSessionCreate,
	payload: dict[str, Any] = Depends(require_child),
	db: AsyncSession = Depends(get_db),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	session_repo: ReadingSessionRepository = Depends(get_reading_session_repository),
) -> ReadingSessionResponse:
	library_id = UUID(payload["library_id"])
	user_id = UUID(payload["sub"])
	session = await LogReadingSessionUseCase(book_repo, session_repo).execute(
		LogReadingSessionInput(
			owned_book_id=body.owned_book_id,
			library_id=library_id,
			user_id=user_id,
			kids_mode_enabled=bool(payload.get("kids_mode_enabled", False)),
			minutes=body.minutes,
			pages=body.pages,
			session_date=body.session_date,
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
