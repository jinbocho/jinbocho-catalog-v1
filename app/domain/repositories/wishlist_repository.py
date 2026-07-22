from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.wishlist_item import WishlistItem


class WishlistRepository(ABC):
    @abstractmethod
    async def get(self, item_id: UUID, library_id: UUID) -> "WishlistItem | None": ...

    @abstractmethod
    async def find_by_id(self, item_id: UUID) -> "WishlistItem | None":
        """Unscoped fetch — callers must check library_id themselves and raise
        PermissionError on mismatch, so cross-tenant access reports 403 (not a
        404 that would collapse the distinction between "doesn't exist" and
        "exists but belongs to someone else"), consistent with how
        BibliographicRecordRepository.find_by_id is used elsewhere."""
        ...

    @abstractmethod
    async def list_by_library(self, library_id: UUID) -> list["WishlistItem"]: ...

    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> list["WishlistItem"]: ...

    @abstractmethod
    async def add(self, item: "WishlistItem") -> "WishlistItem": ...

    @abstractmethod
    async def delete(self, item_id: UUID, library_id: UUID) -> None: ...

    @abstractmethod
    async def exists_for_user_and_record(self, user_id: UUID, record_id: UUID) -> bool: ...

    @abstractmethod
    async def restore(self, item: "WishlistItem") -> "WishlistItem":
        """Upsert preserving id/added_at verbatim — for library import."""
        ...
