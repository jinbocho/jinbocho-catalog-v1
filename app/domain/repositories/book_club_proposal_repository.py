from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import BookClubProposal


class BookClubProposalRepository(ABC):
    @abstractmethod
    async def add(self, proposal: BookClubProposal) -> BookClubProposal: ...

    @abstractmethod
    async def find_by_id(self, proposal_id: UUID) -> BookClubProposal | None: ...

    @abstractmethod
    async def list_by_library(self, library_id: UUID) -> list[BookClubProposal]: ...

    @abstractmethod
    async def delete(self, proposal: BookClubProposal) -> None: ...

    @abstractmethod
    async def delete_all_by_library(self, library_id: UUID) -> None: ...
