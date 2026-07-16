from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import QuizAttempt
from app.domain.repositories import QuizAttemptRepository
from app.infrastructure.models.owned_book_model import OwnedBookModel
from app.infrastructure.models.quiz_attempt_model import QuizAttemptModel


class SQLAlchemyQuizAttemptRepository(QuizAttemptRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: QuizAttemptModel) -> QuizAttempt:
        return QuizAttempt(
            id=model.id,
            owned_book_id=model.owned_book_id,
            user_id=model.user_id,
            question_ids=list(model.question_ids),
            answers=list(model.answers),
            score=model.score,
            total=model.total,
            passed=model.passed,
            created_at=model.created_at,
        )

    async def add(self, attempt: QuizAttempt) -> QuizAttempt:
        model = QuizAttemptModel(
            id=attempt.id,
            owned_book_id=attempt.owned_book_id,
            user_id=attempt.user_id,
            question_ids=attempt.question_ids,
            answers=attempt.answers,
            score=attempt.score,
            total=attempt.total,
            passed=attempt.passed,
            created_at=attempt.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def find_by_id(self, attempt_id: UUID) -> QuizAttempt | None:
        model = await self._session.get(QuizAttemptModel, attempt_id)
        return self._to_entity(model) if model else None

    async def list_by_user_and_library(self, user_id: UUID, library_id: UUID) -> list[QuizAttempt]:
        result = await self._session.execute(
            select(QuizAttemptModel)
            .join(OwnedBookModel, QuizAttemptModel.owned_book_id == OwnedBookModel.id)
            .where(QuizAttemptModel.user_id == user_id, OwnedBookModel.library_id == library_id)
            .order_by(QuizAttemptModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]
