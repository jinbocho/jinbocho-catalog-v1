from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import BookClubMeeting
from app.domain.repositories import BookClubMeetingRepository
from app.infrastructure.models.book_club_meeting_model import BookClubMeetingModel


class SQLAlchemyBookClubMeetingRepository(BookClubMeetingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: BookClubMeetingModel) -> BookClubMeeting:
        return BookClubMeeting(
            id=model.id,
            cycle_id=model.cycle_id,
            scheduled_at=model.scheduled_at,
            note=model.note,
            created_by=model.created_by,
            created_at=model.created_at,
        )

    async def add(self, meeting: BookClubMeeting) -> BookClubMeeting:
        model = BookClubMeetingModel(
            id=meeting.id,
            cycle_id=meeting.cycle_id,
            scheduled_at=meeting.scheduled_at,
            note=meeting.note,
            created_by=meeting.created_by,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def find_by_id(self, meeting_id: UUID) -> BookClubMeeting | None:
        model = await self._session.get(BookClubMeetingModel, meeting_id)
        return self._to_entity(model) if model else None

    async def list_by_cycle(self, cycle_id: UUID) -> list[BookClubMeeting]:
        result = await self._session.execute(
            select(BookClubMeetingModel)
            .where(BookClubMeetingModel.cycle_id == cycle_id)
            .order_by(BookClubMeetingModel.scheduled_at.asc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def delete(self, meeting: BookClubMeeting) -> None:
        model = await self._session.get(BookClubMeetingModel, meeting.id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()
