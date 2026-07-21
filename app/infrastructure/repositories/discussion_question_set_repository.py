from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import DiscussionQuestionSet
from app.domain.repositories import DiscussionQuestionSetRepository
from app.infrastructure.models.discussion_question_set_model import DiscussionQuestionSetModel


class SQLAlchemyDiscussionQuestionSetRepository(DiscussionQuestionSetRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: DiscussionQuestionSetModel) -> DiscussionQuestionSet:
        return DiscussionQuestionSet(
            id=model.id,
            owned_book_id=model.owned_book_id,
            questions=list(model.questions),
            generated_at=model.generated_at,
        )

    async def find_by_book(self, owned_book_id: UUID) -> DiscussionQuestionSet | None:
        result = await self._session.execute(
            select(DiscussionQuestionSetModel).where(DiscussionQuestionSetModel.owned_book_id == owned_book_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, question_set: DiscussionQuestionSet) -> DiscussionQuestionSet:
        model = DiscussionQuestionSetModel(
            id=question_set.id,
            owned_book_id=question_set.owned_book_id,
            questions=question_set.questions,
            generated_at=question_set.generated_at,
        )
        merged = await self._session.merge(model)
        await self._session.flush()
        await self._session.refresh(merged)
        return self._to_entity(merged)
