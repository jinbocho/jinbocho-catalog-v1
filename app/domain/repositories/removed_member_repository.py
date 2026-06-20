from abc import ABC, abstractmethod
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
