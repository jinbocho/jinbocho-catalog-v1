import logging
from dataclasses import dataclass
from uuid import UUID

from app.application.services import QuizScoringService
from app.domain.entities import QuizAttempt, QuizQuestion, QuizSource
from app.domain.repositories import (
    BibliographicRecordRepository,
    OwnedBookRepository,
    QuizAttemptRepository,
    QuizGenerator,
    QuizQuestionRepository,
)
from app.domain.repositories.quiz_generator import QuizBookContext

logger = logging.getLogger(__name__)


@dataclass
class GenerateQuizQuestionsInput:
    owned_book_id: UUID
    library_id: UUID
    kids_mode_enabled: bool
    num_questions: int = 5
    # Free text the caller supplies to steer what the AI questions focus on
    # (e.g. "I'm up to chapter 3"). Providing this always triggers a fresh AI
    # call and appends the results, bypassing the get-or-generate short
    # circuit below — an explicit "generate with context" is a deliberate
    # action, not the passive "open the quiz" call this endpoint also serves.
    extra_context: str | None = None
    # See QuizBookContext.reader_age_band — does not affect the
    # get-or-generate short circuit below, only fresh generations.
    reader_age_band: str | None = None
    # See QuizBookContext.reader_language — same non-effect on the cache
    # short circuit as reader_age_band.
    reader_language: str | None = None


class GenerateQuizQuestionsUseCase:
    """Get-or-generate: if the book already has questions (AI or manual) and
    no extra_context was given, returns them as-is rather than regenerating
    on every call. A manual question authored by a parent beforehand
    pre-empts AI generation the same way. Supplying extra_context always asks
    the AI for more questions and appends them to whatever already exists."""

    def __init__(
        self,
        book_repo: OwnedBookRepository,
        record_repo: BibliographicRecordRepository,
        question_repo: QuizQuestionRepository,
        quiz_generator: QuizGenerator,
    ) -> None:
        self._book_repo = book_repo
        self._record_repo = record_repo
        self._question_repo = question_repo
        self._quiz_generator = quiz_generator

    async def execute(self, input: GenerateQuizQuestionsInput) -> list[QuizQuestion]:
        if not input.kids_mode_enabled:
            raise PermissionError("Kids mode is not enabled for this library")
        book = await self._book_repo.find_by_id(input.owned_book_id)
        if not book:
            raise LookupError("Book not found")
        if book.library_id != input.library_id:
            raise PermissionError("Book does not belong to this library")

        existing = await self._question_repo.list_by_book(input.owned_book_id)
        if existing and not input.extra_context:
            return existing

        record = await self._record_repo.find_by_id(book.bibliographic_record_id)
        if not record:
            return existing

        generated = await self._quiz_generator.generate(
            QuizBookContext(
                title=record.title,
                main_author=record.main_author,
                genre=record.genre,
                incipit=record.incipit,
                language=record.language,
                num_questions=input.num_questions,
                extra_context=input.extra_context,
                reader_age_band=input.reader_age_band,
                reader_language=input.reader_language,
            )
        )
        saved: list[QuizQuestion] = []
        for q in generated:
            saved.append(
                await self._question_repo.add(
                    QuizQuestion(
                        owned_book_id=input.owned_book_id,
                        prompt=q.prompt,
                        choices=q.choices,
                        correct_index=q.correct_index,
                        source=QuizSource.AI,
                    )
                )
            )
        if saved:
            logger.info("AI quiz generated for book %s: %d questions", input.owned_book_id, len(saved))
        return existing + saved


@dataclass
class CreateManualQuizQuestionInput:
    owned_book_id: UUID
    library_id: UUID
    author_user_id: UUID
    prompt: str
    choices: list[str]
    correct_index: int
    kids_mode_enabled: bool


class CreateManualQuizQuestionUseCase:
    def __init__(self, book_repo: OwnedBookRepository, question_repo: QuizQuestionRepository) -> None:
        self._book_repo = book_repo
        self._question_repo = question_repo

    async def execute(self, input: CreateManualQuizQuestionInput) -> QuizQuestion:
        if not input.kids_mode_enabled:
            raise PermissionError("Kids mode is not enabled for this library")
        book = await self._book_repo.find_by_id(input.owned_book_id)
        if not book:
            raise LookupError("Book not found")
        if book.library_id != input.library_id:
            raise PermissionError("Book does not belong to this library")
        if not (0 <= input.correct_index < len(input.choices)):
            raise ValueError("correct_index is out of range for the given choices")

        question = QuizQuestion(
            owned_book_id=input.owned_book_id,
            prompt=input.prompt,
            choices=input.choices,
            correct_index=input.correct_index,
            source=QuizSource.MANUAL,
            author_user_id=input.author_user_id,
        )
        saved = await self._question_repo.add(question)
        logger.info("Manual quiz question added for book %s by %s", input.owned_book_id, input.author_user_id)
        return saved


@dataclass
class ListQuizQuestionsInput:
    owned_book_id: UUID
    library_id: UUID
    kids_mode_enabled: bool


class ListQuizQuestionsUseCase:
    def __init__(self, book_repo: OwnedBookRepository, question_repo: QuizQuestionRepository) -> None:
        self._book_repo = book_repo
        self._question_repo = question_repo

    async def execute(self, input: ListQuizQuestionsInput) -> list[QuizQuestion]:
        if not input.kids_mode_enabled:
            raise PermissionError("Kids mode is not enabled for this library")
        book = await self._book_repo.find_by_id(input.owned_book_id)
        if not book:
            raise LookupError("Book not found")
        if book.library_id != input.library_id:
            raise PermissionError("Book does not belong to this library")
        return await self._question_repo.list_by_book(input.owned_book_id)


@dataclass
class SubmitQuizAttemptInput:
    owned_book_id: UUID
    library_id: UUID
    user_id: UUID
    kids_mode_enabled: bool
    answers: dict[UUID, int]


class SubmitQuizAttemptUseCase:
    def __init__(
        self,
        book_repo: OwnedBookRepository,
        question_repo: QuizQuestionRepository,
        attempt_repo: QuizAttemptRepository,
        scoring_service: QuizScoringService,
    ) -> None:
        self._book_repo = book_repo
        self._question_repo = question_repo
        self._attempt_repo = attempt_repo
        self._scoring_service = scoring_service

    async def execute(self, input: SubmitQuizAttemptInput) -> QuizAttempt:
        if not input.kids_mode_enabled:
            raise PermissionError("Kids mode is not enabled for this library")
        if not input.answers:
            raise ValueError("Submit at least one answer")
        book = await self._book_repo.find_by_id(input.owned_book_id)
        if not book:
            raise LookupError("Book not found")
        if book.library_id != input.library_id:
            raise PermissionError("Book does not belong to this library")

        question_ids = list(input.answers.keys())
        questions = await self._question_repo.find_by_ids(question_ids)
        if len(questions) != len(question_ids) or any(q.owned_book_id != input.owned_book_id for q in questions):
            raise LookupError("One or more questions not found for this book")

        result = self._scoring_service.score(questions, input.answers)
        attempt = QuizAttempt(
            owned_book_id=input.owned_book_id,
            user_id=input.user_id,
            question_ids=question_ids,
            answers=[input.answers[qid] for qid in question_ids],
            score=result.score,
            total=result.total,
            passed=result.passed,
        )
        saved = await self._attempt_repo.add(attempt)
        logger.info(
            "Quiz attempt submitted by user %s for book %s: %d/%d",
            input.user_id, input.owned_book_id, result.score, result.total,
        )
        return saved


@dataclass
class ListQuizAttemptsInput:
    target_user_id: UUID
    library_id: UUID
    requester_user_id: UUID
    requester_role: str
    kids_mode_enabled: bool


class ListQuizAttemptsUseCase:
    """Same child-own / parent-any authorization split as ListReadingSessionsUseCase."""

    def __init__(self, attempt_repo: QuizAttemptRepository) -> None:
        self._attempt_repo = attempt_repo

    async def execute(self, input: ListQuizAttemptsInput) -> list[QuizAttempt]:
        if not input.kids_mode_enabled:
            raise PermissionError("Kids mode is not enabled for this library")
        is_self = input.target_user_id == input.requester_user_id
        is_parent = input.requester_role in ("admin", "editor")
        if not is_self and not is_parent:
            raise PermissionError("Cannot view another user's quiz attempts")
        return await self._attempt_repo.list_by_user_and_library(input.target_user_id, input.library_id)


@dataclass
class QuizAnswerDetail:
    question_id: UUID
    prompt: str
    choices: list[str]
    correct_index: int
    selected_index: int
    is_correct: bool


@dataclass
class QuizAttemptDetail:
    attempt: QuizAttempt
    answers: list[QuizAnswerDetail]


@dataclass
class GetQuizAttemptDetailInput:
    attempt_id: UUID
    library_id: UUID
    requester_user_id: UUID
    requester_role: str
    kids_mode_enabled: bool


class GetQuizAttemptDetailUseCase:
    """Powers the parent dashboard's "view answers" modal — same self-or-parent
    split as ListQuizAttemptsUseCase, plus the per-question answer key zipped
    against what the child actually selected."""

    def __init__(
        self,
        book_repo: OwnedBookRepository,
        question_repo: QuizQuestionRepository,
        attempt_repo: QuizAttemptRepository,
    ) -> None:
        self._book_repo = book_repo
        self._question_repo = question_repo
        self._attempt_repo = attempt_repo

    async def execute(self, input: GetQuizAttemptDetailInput) -> QuizAttemptDetail:
        if not input.kids_mode_enabled:
            raise PermissionError("Kids mode is not enabled for this library")
        attempt = await self._attempt_repo.find_by_id(input.attempt_id)
        if not attempt:
            raise LookupError("Quiz attempt not found")
        book = await self._book_repo.find_by_id(attempt.owned_book_id)
        if not book:
            raise LookupError("Book not found")
        if book.library_id != input.library_id:
            raise PermissionError("Attempt does not belong to this library")

        is_self = attempt.user_id == input.requester_user_id
        is_parent = input.requester_role in ("admin", "editor")
        if not is_self and not is_parent:
            raise PermissionError("Cannot view another user's quiz attempt")

        questions_by_id = {q.id: q for q in await self._question_repo.find_by_ids(attempt.question_ids)}
        answers: list[QuizAnswerDetail] = []
        for question_id, selected_index in zip(attempt.question_ids, attempt.answers, strict=True):
            question = questions_by_id.get(question_id)
            if question is None:
                continue
            answers.append(
                QuizAnswerDetail(
                    question_id=question_id,
                    prompt=question.prompt,
                    choices=question.choices,
                    correct_index=question.correct_index,
                    selected_index=selected_index,
                    is_correct=selected_index == question.correct_index,
                )
            )
        return QuizAttemptDetail(attempt=attempt, answers=answers)
