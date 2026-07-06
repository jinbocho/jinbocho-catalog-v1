import logging
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import LibraryRole, RemovedMember
from app.domain.repositories import RemovedMemberRepository

logger = logging.getLogger(__name__)


@dataclass
class RecordRemovedMemberInput:
	library_id: UUID
	id: UUID
	full_name: str
	email: str
	role: LibraryRole


class RecordRemovedMemberUseCase:
	"""Called by the FE right before it deletes a library member in
	auth-service — auth-service hard-deletes the row, so this is the last
	moment the real name/email/role can be captured. Without it, a future
	export/import has no way to recreate this person's account; their old
	owner_id/current_reader_id/etc. references would just have to be left
	unresolved (no owner) on import."""

	def __init__(self, removed_member_repo: RemovedMemberRepository):
		self._removed_member_repo = removed_member_repo

	async def execute(self, input: RecordRemovedMemberInput) -> RemovedMember:
		saved = await self._removed_member_repo.save(
			RemovedMember(
				id=input.id,
				library_id=input.library_id,
				full_name=input.full_name,
				email=input.email,
				role=input.role,
			)
		)
		logger.info("Removed member %s recorded for library %s", input.id, input.library_id)
		return saved
