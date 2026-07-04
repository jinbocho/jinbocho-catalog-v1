from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.domain.entities import RemovedMember


class RemovedMemberRepository(ABC):
	@abstractmethod
	async def save(self, member: RemovedMember) -> RemovedMember:
		"""Upsert by id — recording the same removal twice (e.g. a retried
		request) overwrites the snapshot rather than duplicating it."""
		...

	@abstractmethod
	async def find_all_by_family(self, family_id: UUID) -> list[RemovedMember]: ...

	@abstractmethod
	async def delete_all_by_family(self, family_id: UUID) -> None:
		"""Used by full account deletion."""
		...

	@abstractmethod
	async def delete_expired(self, older_than: datetime) -> int:
		"""Global sweep (not family-scoped) for the retention job — deletes
		every snapshot removed before ``older_than`` and returns the count."""
		...
