from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import BookClubPost


class BookClubPostRepository(ABC):
    @abstractmethod
    async def add(self, post: BookClubPost) -> BookClubPost: ...

    @abstractmethod
    async def find_by_id(self, post_id: UUID) -> BookClubPost | None: ...

    @abstractmethod
    async def list_by_cycle(self, cycle_id: UUID) -> list[BookClubPost]: ...

    @abstractmethod
    async def delete(self, post: BookClubPost) -> None: ...
