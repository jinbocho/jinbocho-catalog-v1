from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import BookClubParticipant


class BookClubParticipantRepository(ABC):
    @abstractmethod
    async def add(self, participant: BookClubParticipant) -> BookClubParticipant: ...

    @abstractmethod
    async def save(self, participant: BookClubParticipant) -> BookClubParticipant: ...

    @abstractmethod
    async def find_by_cycle_and_user(self, cycle_id: UUID, user_id: UUID) -> BookClubParticipant | None: ...

    @abstractmethod
    async def list_by_cycle(self, cycle_id: UUID) -> list[BookClubParticipant]: ...
