from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import FamilyRole, RemovedMember
from app.domain.repositories import RemovedMemberRepository
from app.infrastructure.models import RemovedMemberModel


class SQLAlchemyRemovedMemberRepository(RemovedMemberRepository):
	def __init__(self, session: AsyncSession) -> None:
		self._session = session

	@staticmethod
	def _to_entity(model: RemovedMemberModel) -> RemovedMember:
		return RemovedMember(
			id=model.id,
			family_id=model.family_id,
			full_name=model.full_name,
			email=model.email,
			role=FamilyRole(model.role),
			removed_at=model.removed_at,
		)

	async def save(self, member: RemovedMember) -> RemovedMember:
		model = await self._session.get(RemovedMemberModel, member.id)
		if model is None:
			model = RemovedMemberModel(
				id=member.id,
				family_id=member.family_id,
				full_name=member.full_name,
				email=member.email,
				role=member.role,
				removed_at=member.removed_at,
			)
			self._session.add(model)
		else:
			model.family_id = member.family_id
			model.full_name = member.full_name
			model.email = member.email
			model.role = member.role
			model.removed_at = member.removed_at
		await self._session.flush()
		await self._session.refresh(model)
		return self._to_entity(model)

	async def find_all_by_family(self, family_id: UUID) -> list[RemovedMember]:
		result = await self._session.execute(
			select(RemovedMemberModel).where(RemovedMemberModel.family_id == family_id)
		)
		return [self._to_entity(model) for model in result.scalars().all()]

	async def delete_all_by_family(self, family_id: UUID) -> None:
		await self._session.execute(sa_delete(RemovedMemberModel).where(RemovedMemberModel.family_id == family_id))
		await self._session.flush()
