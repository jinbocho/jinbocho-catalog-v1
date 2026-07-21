from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import BookClubQuestionSet
from app.domain.repositories import BookClubQuestionSetRepository
from app.infrastructure.models.book_club_question_set_model import BookClubQuestionSetModel


class SQLAlchemyBookClubQuestionSetRepository(BookClubQuestionSetRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: BookClubQuestionSetModel) -> BookClubQuestionSet:
        return BookClubQuestionSet(
            id=model.id,
            cycle_id=model.cycle_id,
            language=model.language,
            questions=list(model.questions),
            generated_at=model.generated_at,
        )

    async def find_by_cycle_and_language(
        self, cycle_id: UUID, language: str
    ) -> BookClubQuestionSet | None:
        result = await self._session.execute(
            select(BookClubQuestionSetModel).where(
                BookClubQuestionSetModel.cycle_id == cycle_id,
                BookClubQuestionSetModel.language == language,
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, question_set: BookClubQuestionSet) -> BookClubQuestionSet:
        result = await self._session.execute(
            select(BookClubQuestionSetModel).where(
                BookClubQuestionSetModel.cycle_id == question_set.cycle_id,
                BookClubQuestionSetModel.language == question_set.language,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            model = BookClubQuestionSetModel(
                id=question_set.id,
                cycle_id=question_set.cycle_id,
                language=question_set.language,
                questions=question_set.questions,
            )
            self._session.add(model)
        else:
            model.questions = question_set.questions
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)
