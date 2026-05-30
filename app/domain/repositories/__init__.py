from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.entities import (
    BibliographicRecord,
    BookHistory,
    Bookcase,
    IsbnLookupCache,
    OwnedBook,
    Room,
    Section,
    Shelf,
)


class RoomRepository(ABC):
    @abstractmethod
    async def find_by_id(self, room_id: UUID) -> Optional[Room]: ...

    @abstractmethod
    async def find_all_by_family(self, family_id: UUID, limit: int = 50, offset: int = 0) -> list[Room]: ...

    @abstractmethod
    async def save(self, room: Room) -> Room: ...

    @abstractmethod
    async def delete(self, room_id: UUID) -> None: ...


class BookcaseRepository(ABC):
    @abstractmethod
    async def find_by_id(self, bookcase_id: UUID) -> Optional[Bookcase]: ...

    @abstractmethod
    async def find_all_by_family(
        self,
        family_id: UUID,
        room_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Bookcase]: ...

    @abstractmethod
    async def save(self, bookcase: Bookcase) -> Bookcase: ...

    @abstractmethod
    async def delete(self, bookcase_id: UUID) -> None: ...


class SectionRepository(ABC):
    @abstractmethod
    async def find_by_id(self, section_id: UUID) -> Optional[Section]: ...

    @abstractmethod
    async def find_all_by_bookcase(self, bookcase_id: UUID, limit: int = 50, offset: int = 0) -> list[Section]: ...

    @abstractmethod
    async def find_all_by_family(
        self,
        family_id: UUID,
        bookcase_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Section]: ...

    @abstractmethod
    async def save(self, section: Section) -> Section: ...

    @abstractmethod
    async def delete(self, section_id: UUID) -> None: ...


class ShelfRepository(ABC):
    @abstractmethod
    async def find_by_id(self, shelf_id: UUID) -> Optional[Shelf]: ...

    @abstractmethod
    async def find_all_by_section(self, section_id: UUID, limit: int = 50, offset: int = 0) -> list[Shelf]: ...

    @abstractmethod
    async def find_all_by_family(
        self,
        family_id: UUID,
        section_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Shelf]: ...

    @abstractmethod
    async def save(self, shelf: Shelf) -> Shelf: ...

    @abstractmethod
    async def delete(self, shelf_id: UUID) -> None: ...


class BibliographicRecordRepository(ABC):
    @abstractmethod
    async def find_by_id(self, record_id: UUID) -> Optional[BibliographicRecord]: ...

    @abstractmethod
    async def find_by_isbn(self, family_id: UUID, isbn: str) -> Optional[BibliographicRecord]: ...

    @abstractmethod
    async def find_all_by_family(
        self,
        family_id: UUID,
        q: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[BibliographicRecord]: ...

    @abstractmethod
    async def find_all_by_ids(self, record_ids: list[UUID]) -> list[BibliographicRecord]: ...

    @abstractmethod
    async def save(self, record: BibliographicRecord) -> BibliographicRecord: ...

    @abstractmethod
    async def delete(self, record_id: UUID) -> None: ...


class OwnedBookRepository(ABC):
    @abstractmethod
    async def find_by_id(self, book_id: UUID) -> Optional[OwnedBook]: ...

    @abstractmethod
    async def find_all_by_family(
        self,
        family_id: UUID,
        shelf_id: Optional[UUID] = None,
        reading_status: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[OwnedBook]: ...

    @abstractmethod
    async def find_all_by_shelf_ids(self, shelf_ids: list[UUID]) -> list[OwnedBook]: ...

    @abstractmethod
    async def exists_by_bibliographic_record_id(self, record_id: UUID) -> bool: ...

    @abstractmethod
    async def save(self, owned_book: OwnedBook) -> OwnedBook: ...

    @abstractmethod
    async def delete(self, book_id: UUID) -> None: ...


class BookHistoryRepository(ABC):
    @abstractmethod
    async def find_by_book(self, book_id: UUID, limit: int = 50, offset: int = 0) -> list[BookHistory]: ...

    @abstractmethod
    async def save(self, history: BookHistory) -> BookHistory: ...


class IsbnLookupCacheRepository(ABC):
    @abstractmethod
    async def find_by_isbn(self, isbn: str) -> Optional[IsbnLookupCache]: ...

    @abstractmethod
    async def save(self, entity: IsbnLookupCache) -> IsbnLookupCache: ...
