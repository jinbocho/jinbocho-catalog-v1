from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.domain.entities import BookAbandonment


class BookAbandonmentRepository(ABC):
    @abstractmethod
    async def add(
        self, owned_book_id: UUID, user_id: UUID, abandoned_at: datetime | None = None
    ) -> BookAbandonment: ...

    @abstractmethod
    async def remove(self, owned_book_id: UUID, user_id: UUID) -> None: ...

    @abstractmethod
    async def is_abandoned(self, owned_book_id: UUID, user_id: UUID) -> bool:
        """Whether user_id has marked owned_book_id as abandoned — drives the
        per-member reading_status shown to that user."""
        ...

    @abstractmethod
    async def list_abandoned_book_ids(self, owned_book_ids: list[UUID], user_id: UUID) -> set[UUID]:
        """Subset of owned_book_ids that user_id has marked as abandoned —
        batch form of is_abandoned(), used when rendering a list of books."""
        ...
