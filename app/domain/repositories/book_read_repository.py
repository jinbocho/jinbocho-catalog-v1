from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import BookRead


class BookReadRepository(ABC):
    @abstractmethod
    async def add(self, owned_book_id: UUID, user_id: UUID) -> BookRead: ...

    @abstractmethod
    async def remove(self, owned_book_id: UUID, user_id: UUID) -> None: ...

    @abstractmethod
    async def list_by_book(self, owned_book_id: UUID) -> list[BookRead]: ...

    @abstractmethod
    async def list_by_family(self, family_id: UUID) -> list[BookRead]: ...

    @abstractmethod
    async def restore(self, book_read: BookRead) -> BookRead:
        """Upsert preserving id/read_at verbatim — for library import, unlike
        add() which always stamps read_at as now and generates a fresh id."""
        ...
