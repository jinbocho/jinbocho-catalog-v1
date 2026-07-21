from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import BookClubParticipant
from app.domain.entities.book_club_participant import ParticipantStatus
from app.domain.repositories import BookClubParticipantRepository
from app.infrastructure.models.book_club_participant_model import BookClubParticipantModel


class SQLAlchemyBookClubParticipantRepository(BookClubParticipantRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: BookClubParticipantModel) -> BookClubParticipant:
        return BookClubParticipant(
            id=model.id,
            cycle_id=model.cycle_id,
            user_id=model.user_id,
            status=ParticipantStatus(model.status),
            joined_at=model.joined_at,
        )

    async def add(self, participant: BookClubParticipant) -> BookClubParticipant:
        model = BookClubParticipantModel(
            id=participant.id,
            cycle_id=participant.cycle_id,
            user_id=participant.user_id,
            status=participant.status.value,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def save(self, participant: BookClubParticipant) -> BookClubParticipant:
        model = await self._session.get(BookClubParticipantModel, participant.id)
        if model is None:
            raise LookupError(f"BookClubParticipant {participant.id} not found")
        model.status = participant.status.value
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def find_by_cycle_and_user(self, cycle_id: UUID, user_id: UUID) -> BookClubParticipant | None:
        result = await self._session.execute(
            select(BookClubParticipantModel).where(
                BookClubParticipantModel.cycle_id == cycle_id,
                BookClubParticipantModel.user_id == user_id,
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_cycle(self, cycle_id: UUID) -> list[BookClubParticipant]:
        result = await self._session.execute(
            select(BookClubParticipantModel)
            .where(BookClubParticipantModel.cycle_id == cycle_id)
            .order_by(BookClubParticipantModel.joined_at.asc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]
