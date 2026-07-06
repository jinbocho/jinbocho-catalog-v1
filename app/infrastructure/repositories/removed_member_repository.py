from datetime import datetime
from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import LibraryRole, RemovedMember
from app.domain.repositories import RemovedMemberRepository
from app.infrastructure.models import RemovedMemberModel


class SQLAlchemyRemovedMemberRepository(RemovedMemberRepository):
	def __init__(self, session: AsyncSession) -> None:
		self._session = session

	@staticmethod
	def _to_entity(model: RemovedMemberModel) -> RemovedMember:
		return RemovedMember(
			id=model.id,
			library_id=model.library_id,
			full_name=model.full_name,
			email=model.email,
			role=LibraryRole(model.role),
			removed_at=model.removed_at,
		)

	async def save(self, member: RemovedMember) -> RemovedMember:
		model = await self._session.get(RemovedMemberModel, member.id)
		if model is None:
			model = RemovedMemberModel(
				id=member.id,
				library_id=member.library_id,
				full_name=member.full_name,
				email=member.email,
				role=member.role,
				removed_at=member.removed_at,
			)
			self._session.add(model)
		else:
			model.library_id = member.library_id
			model.full_name = member.full_name
			model.email = member.email
			model.role = member.role
			model.removed_at = member.removed_at
		await self._session.flush()
		await self._session.refresh(model)
		return self._to_entity(model)

	async def find_all_by_library(self, library_id: UUID) -> list[RemovedMember]:
		result = await self._session.execute(
			select(RemovedMemberModel).where(RemovedMemberModel.library_id == library_id)
		)
		return [self._to_entity(model) for model in result.scalars().all()]

	async def delete_all_by_library(self, library_id: UUID) -> None:
		await self._session.execute(sa_delete(RemovedMemberModel).where(RemovedMemberModel.library_id == library_id))
		await self._session.flush()

	async def delete_expired(self, older_than: datetime) -> int:
		result = await self._session.execute(
			sa_delete(RemovedMemberModel).where(RemovedMemberModel.removed_at < older_than)
		)
		await self._session.flush()
		return result.rowcount or 0
