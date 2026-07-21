from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import FamilyChallenge


class FamilyChallengeRepository(ABC):
    @abstractmethod
    async def add(self, challenge: FamilyChallenge) -> FamilyChallenge: ...

    @abstractmethod
    async def find_by_id(self, challenge_id: UUID) -> FamilyChallenge | None: ...

    @abstractmethod
    async def list_by_library(self, library_id: UUID) -> list[FamilyChallenge]: ...

    @abstractmethod
    async def delete(self, challenge_id: UUID) -> None: ...
