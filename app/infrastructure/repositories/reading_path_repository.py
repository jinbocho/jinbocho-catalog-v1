from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import ReadingPath, ReadingPathSource
from app.domain.repositories import ReadingPathRepository
from app.infrastructure.models.reading_path_model import ReadingPathModel


class SQLAlchemyReadingPathRepository(ReadingPathRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: ReadingPathModel) -> ReadingPath:
        return ReadingPath(
            id=model.id,
            library_id=model.library_id,
            title=model.title,
            description=model.description,
            book_ids=list(model.book_ids),
            target_band=model.target_band,
            source=ReadingPathSource(model.source),
            created_by=model.created_by,
            created_at=model.created_at,
        )

    async def add(self, path: ReadingPath) -> ReadingPath:
        model = ReadingPathModel(
            id=path.id,
            library_id=path.library_id,
            title=path.title,
            description=path.description,
            book_ids=path.book_ids,
            target_band=path.target_band,
            source=path.source.value,
            created_by=path.created_by,
            created_at=path.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def find_by_id(self, path_id: UUID) -> ReadingPath | None:
        result = await self._session.execute(select(ReadingPathModel).where(ReadingPathModel.id == path_id))
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_library(self, library_id: UUID) -> list[ReadingPath]:
        result = await self._session.execute(
            select(ReadingPathModel)
            .where(ReadingPathModel.library_id == library_id)
            .order_by(ReadingPathModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def delete(self, path_id: UUID) -> None:
        model = await self._session.get(ReadingPathModel, path_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()
