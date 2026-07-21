from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import BookClubMeeting


class BookClubMeetingRepository(ABC):
    @abstractmethod
    async def add(self, meeting: BookClubMeeting) -> BookClubMeeting: ...

    @abstractmethod
    async def find_by_id(self, meeting_id: UUID) -> BookClubMeeting | None: ...

    @abstractmethod
    async def list_by_cycle(self, cycle_id: UUID) -> list[BookClubMeeting]: ...

    @abstractmethod
    async def delete(self, meeting: BookClubMeeting) -> None: ...
