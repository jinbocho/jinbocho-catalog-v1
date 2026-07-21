from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import BookClubCycle
from app.domain.entities.book_club_cycle import BookClubCycleStatus
from app.domain.repositories import BookClubCycleRepository
from app.infrastructure.models.book_club_cycle_model import BookClubCycleModel


class SQLAlchemyBookClubCycleRepository(BookClubCycleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: BookClubCycleModel) -> BookClubCycle:
        return BookClubCycle(
            id=model.id,
            library_id=model.library_id,
            bibliographic_record_id=model.bibliographic_record_id,
            owned_book_id=model.owned_book_id,
            title=model.title,
            created_by=model.created_by,
            status=BookClubCycleStatus(model.status),
            reading_start=model.reading_start,
            reading_end=model.reading_end,
            created_at=model.created_at,
        )

    async def add(self, cycle: BookClubCycle) -> BookClubCycle:
        model = BookClubCycleModel(
            id=cycle.id,
            library_id=cycle.library_id,
            bibliographic_record_id=cycle.bibliographic_record_id,
            owned_book_id=cycle.owned_book_id,
            title=cycle.title,
            created_by=cycle.created_by,
            status=cycle.status.value,
            reading_start=cycle.reading_start,
            reading_end=cycle.reading_end,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def save(self, cycle: BookClubCycle) -> BookClubCycle:
        model = await self._session.get(BookClubCycleModel, cycle.id)
        if model is None:
            raise LookupError(f"BookClubCycle {cycle.id} not found")
        model.title = cycle.title
        model.status = cycle.status.value
        model.owned_book_id = cycle.owned_book_id
        model.reading_start = cycle.reading_start
        model.reading_end = cycle.reading_end
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def find_by_id(self, cycle_id: UUID) -> BookClubCycle | None:
        model = await self._session.get(BookClubCycleModel, cycle_id)
        return self._to_entity(model) if model else None

    async def list_by_library(self, library_id: UUID) -> list[BookClubCycle]:
        result = await self._session.execute(
            select(BookClubCycleModel)
            .where(BookClubCycleModel.library_id == library_id)
            .order_by(BookClubCycleModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]
