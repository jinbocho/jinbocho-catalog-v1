from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import ChallengeMetric, FamilyChallenge
from app.domain.repositories import FamilyChallengeRepository
from app.infrastructure.models.family_challenge_model import FamilyChallengeModel


class SQLAlchemyFamilyChallengeRepository(FamilyChallengeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: FamilyChallengeModel) -> FamilyChallenge:
        return FamilyChallenge(
            id=model.id,
            library_id=model.library_id,
            title=model.title,
            metric=ChallengeMetric(model.metric),
            target=model.target,
            starts_on=model.starts_on,
            ends_on=model.ends_on,
            created_by=model.created_by,
            created_at=model.created_at,
        )

    async def add(self, challenge: FamilyChallenge) -> FamilyChallenge:
        model = FamilyChallengeModel(
            id=challenge.id,
            library_id=challenge.library_id,
            title=challenge.title,
            metric=challenge.metric.value,
            target=challenge.target,
            starts_on=challenge.starts_on,
            ends_on=challenge.ends_on,
            created_by=challenge.created_by,
            created_at=challenge.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def find_by_id(self, challenge_id: UUID) -> FamilyChallenge | None:
        result = await self._session.execute(
            select(FamilyChallengeModel).where(FamilyChallengeModel.id == challenge_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_library(self, library_id: UUID) -> list[FamilyChallenge]:
        result = await self._session.execute(
            select(FamilyChallengeModel)
            .where(FamilyChallengeModel.library_id == library_id)
            .order_by(FamilyChallengeModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def delete(self, challenge_id: UUID) -> None:
        model = await self._session.get(FamilyChallengeModel, challenge_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()
