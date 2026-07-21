from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import BookClubVote


class BookClubVoteRepository(ABC):
    @abstractmethod
    async def add(self, vote: BookClubVote) -> BookClubVote: ...

    @abstractmethod
    async def find_by_proposal_and_user(self, proposal_id: UUID, user_id: UUID) -> BookClubVote | None: ...

    @abstractmethod
    async def delete(self, vote: BookClubVote) -> None: ...

    @abstractmethod
    async def list_by_proposals(self, proposal_ids: list[UUID]) -> list[BookClubVote]: ...
