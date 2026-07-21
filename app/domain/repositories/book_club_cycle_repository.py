from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import BookClubCycle


class BookClubCycleRepository(ABC):
    @abstractmethod
    async def add(self, cycle: BookClubCycle) -> BookClubCycle: ...

    @abstractmethod
    async def save(self, cycle: BookClubCycle) -> BookClubCycle: ...

    @abstractmethod
    async def find_by_id(self, cycle_id: UUID) -> BookClubCycle | None: ...

    @abstractmethod
    async def list_by_library(self, library_id: UUID) -> list[BookClubCycle]: ...
