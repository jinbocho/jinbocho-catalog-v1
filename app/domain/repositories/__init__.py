from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.entities import BibliographicRecord, BookHistory, Bookcase, OwnedBook, Room, Section, Shelf


class RoomRepository(ABC):
    @abstractmethod
    async def save(self, room: Room) -> Room: ...

    @abstractmethod
    async def find_by_id(self, room_id: UUID) -> Optional[Room]: ...


class BookcaseRepository(ABC):
    @abstractmethod
    async def save(self, bookcase: Bookcase) -> Bookcase: ...

    @abstractmethod
    async def find_by_id(self, bookcase_id: UUID) -> Optional[Bookcase]: ...


class SectionRepository(ABC):
    @abstractmethod
    async def save(self, section: Section) -> Section: ...


class ShelfRepository(ABC):
    @abstractmethod
    async def save(self, shelf: Shelf) -> Shelf: ...


class BibliographicRecordRepository(ABC):
    @abstractmethod
    async def save(self, record: BibliographicRecord) -> BibliographicRecord: ...

    @abstractmethod
    async def find_by_id(self, record_id: UUID) -> Optional[BibliographicRecord]: ...


class OwnedBookRepository(ABC):
    @abstractmethod
    async def save(self, book: OwnedBook) -> OwnedBook: ...

    @abstractmethod
    async def find_by_id(self, book_id: UUID) -> Optional[OwnedBook]: ...


class BookHistoryRepository(ABC):
    @abstractmethod
    async def save(self, event: BookHistory) -> BookHistory: ...
