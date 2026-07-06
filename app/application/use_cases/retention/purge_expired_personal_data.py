import logging
from dataclasses import dataclass
from datetime import datetime

from app.domain.repositories import RemovedMemberRepository

logger = logging.getLogger(__name__)


@dataclass
class PurgeExpiredPersonalDataOutput:
	removed_members_deleted: int


class PurgeExpiredPersonalDataUseCase:
	"""GDPR Art. 5(1)(e) storage-limitation sweep — deletes former-member
	snapshots (``removed_members``) once ``settings.retention_months`` (12 by
	default) has passed since their removal.

	Book loans are deliberately NOT touched here: a loan's borrower_name
	belongs to the lending library's own history (comparable to a personal
	note — "I lent this to so-and-so"), not to an account with its own
	lifecycle — most borrowers were never a member at all. That data persists
	for as long as the library's account exists and is only removed by full
	account deletion (DeleteLibraryDataUseCase), never by this time-based sweep.

	Not library-scoped: this runs as a global scheduled job (see
	app/core/lifespan.py), the same way SendLoanRemindersUseCase does.
	"""

	def __init__(self, removed_member_repo: RemovedMemberRepository) -> None:
		self._removed_member_repo = removed_member_repo

	async def execute(self, older_than: datetime) -> PurgeExpiredPersonalDataOutput:
		removed_members_deleted = await self._removed_member_repo.delete_expired(older_than)
		return PurgeExpiredPersonalDataOutput(removed_members_deleted=removed_members_deleted)
