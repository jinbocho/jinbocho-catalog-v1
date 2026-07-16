from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import QuizQuestion, QuizSource
from app.domain.repositories import QuizQuestionRepository
from app.infrastructure.models.quiz_question_model import QuizQuestionModel


class SQLAlchemyQuizQuestionRepository(QuizQuestionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: QuizQuestionModel) -> QuizQuestion:
        return QuizQuestion(
            id=model.id,
            owned_book_id=model.owned_book_id,
            prompt=model.prompt,
            choices=list(model.choices),
            correct_index=model.correct_index,
            source=QuizSource(model.source),
            author_user_id=model.author_user_id,
            created_at=model.created_at,
        )

    async def add(self, question: QuizQuestion) -> QuizQuestion:
        model = QuizQuestionModel(
            id=question.id,
            owned_book_id=question.owned_book_id,
            prompt=question.prompt,
            choices=question.choices,
            correct_index=question.correct_index,
            source=question.source.value,
            author_user_id=question.author_user_id,
            created_at=question.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def list_by_book(self, owned_book_id: UUID) -> list[QuizQuestion]:
        result = await self._session.execute(
            select(QuizQuestionModel)
            .where(QuizQuestionModel.owned_book_id == owned_book_id)
            .order_by(QuizQuestionModel.created_at)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def find_by_ids(self, ids: list[UUID]) -> list[QuizQuestion]:
        if not ids:
            return []
        result = await self._session.execute(select(QuizQuestionModel).where(QuizQuestionModel.id.in_(ids)))
        return [self._to_entity(m) for m in result.scalars().all()]
