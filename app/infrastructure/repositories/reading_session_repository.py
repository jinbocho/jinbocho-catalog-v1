from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import ReadingSession
from app.domain.repositories import ReadingSessionRepository
from app.infrastructure.models.owned_book_model import OwnedBookModel
from app.infrastructure.models.reading_session_model import ReadingSessionModel


class SQLAlchemyReadingSessionRepository(ReadingSessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: ReadingSessionModel) -> ReadingSession:
        return ReadingSession(
            id=model.id,
            owned_book_id=model.owned_book_id,
            user_id=model.user_id,
            minutes=model.minutes,
            pages=model.pages,
            session_date=model.session_date,
            created_at=model.created_at,
        )

    async def add(self, session: ReadingSession) -> ReadingSession:
        model = ReadingSessionModel(
            id=session.id,
            owned_book_id=session.owned_book_id,
            user_id=session.user_id,
            minutes=session.minutes,
            pages=session.pages,
            session_date=session.session_date,
            created_at=session.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def list_by_user_and_library(self, user_id: UUID, library_id: UUID) -> list[ReadingSession]:
        result = await self._session.execute(
            select(ReadingSessionModel)
            .join(OwnedBookModel, ReadingSessionModel.owned_book_id == OwnedBookModel.id)
            .where(ReadingSessionModel.user_id == user_id, OwnedBookModel.library_id == library_id)
            .order_by(ReadingSessionModel.session_date.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]
