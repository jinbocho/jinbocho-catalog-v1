from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import FamilyRole, RemovedMember
from app.domain.repositories import RemovedMemberRepository


@dataclass
class RecordRemovedMemberInput:
	family_id: UUID
	id: UUID
	full_name: str
	email: str
	role: FamilyRole


class RecordRemovedMemberUseCase:
	"""Called by the FE right before it deletes a family member in
	auth-service — auth-service hard-deletes the row, so this is the last
	moment the real name/email/role can be captured. Without it, a future
	export/import has no way to recreate this person's account; their old
	owner_id/current_reader_id/etc. references would just have to be left
	unresolved (no owner) on import."""

	def __init__(self, removed_member_repo: RemovedMemberRepository):
		self._removed_member_repo = removed_member_repo

	async def execute(self, input: RecordRemovedMemberInput) -> RemovedMember:
		return await self._removed_member_repo.save(
			RemovedMember(
				id=input.id,
				family_id=input.family_id,
				full_name=input.full_name,
				email=input.email,
				role=input.role,
			)
		)
