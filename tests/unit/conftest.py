import pytest
from uuid import uuid4, UUID
from datetime import datetime

from app.domain.entities import Room, Bookcase, Section, Shelf, BibliographicRecord, OwnedBook
from app.domain.repositories import (
	RoomRepository,
	BookcaseRepository,
	SectionRepository,
	ShelfRepository,
	BibliographicRecordRepository,
	OwnedBookRepository,
	BookHistoryRepository,
	IsbnLookupCacheRepository,
)


class MockRoomRepository(RoomRepository):
	def __init__(self):
		self.rooms = {}

	async def save(self, room: Room) -> Room:
		self.rooms[room.id] = room
		return room

	async def find_by_id(self, room_id: UUID) -> Room | None:
		return self.rooms.get(room_id)

	async def find_all_by_family(self, family_id: UUID, limit: int = 50, offset: int = 0) -> list[Room]:
		return [r for r in self.rooms.values() if r.family_id == family_id][offset:offset+limit]

	async def delete(self, room_id: UUID) -> None:
		self.rooms.pop(room_id, None)


class MockBookcaseRepository(BookcaseRepository):
	def __init__(self):
		self.bookcases = {}

	async def save(self, bookcase: Bookcase) -> Bookcase:
		self.bookcases[bookcase.id] = bookcase
		return bookcase

	async def find_by_id(self, bookcase_id: UUID) -> Bookcase | None:
		return self.bookcases.get(bookcase_id)

	async def find_all_by_family(self, family_id: UUID, room_id: UUID | None = None, limit: int = 50, offset: int = 0) -> list[Bookcase]:
		items = [b for b in self.bookcases.values() if b.family_id == family_id]
		if room_id:
			items = [b for b in items if b.room_id == room_id]
		return items[offset:offset+limit]

	async def delete(self, bookcase_id: UUID) -> None:
		self.bookcases.pop(bookcase_id, None)


class MockBibliographicRecordRepository(BibliographicRecordRepository):
	def __init__(self):
		self.records = {}

	async def save(self, record: BibliographicRecord) -> BibliographicRecord:
		self.records[record.id] = record
		return record

	async def find_by_id(self, record_id: UUID) -> BibliographicRecord | None:
		return self.records.get(record_id)

	async def find_by_isbn(self, family_id: UUID, isbn: str) -> BibliographicRecord | None:
		for r in self.records.values():
			if r.family_id == family_id and r.isbn == isbn:
				return r
		return None

	async def find_all_by_family(self, family_id: UUID, q: str | None = None, limit: int = 50, offset: int = 0) -> list[BibliographicRecord]:
		items = [r for r in self.records.values() if r.family_id == family_id]
		if q:
			items = [r for r in items if q.lower() in r.title.lower()]
		return items[offset:offset+limit]

	async def find_all_by_ids(self, ids: list[UUID]) -> list[BibliographicRecord]:
		return [self.records[id] for id in ids if id in self.records]

	async def delete(self, record_id: UUID) -> None:
		self.records.pop(record_id, None)


class MockOwnedBookRepository(OwnedBookRepository):
	def __init__(self):
		self.books = {}

	async def save(self, book: OwnedBook) -> OwnedBook:
		self.books[book.id] = book
		return book

	async def find_by_id(self, book_id: UUID) -> OwnedBook | None:
		return self.books.get(book_id)

	async def find_all_by_family(self, family_id: UUID, limit: int = 50, offset: int = 0) -> list[OwnedBook]:
		items = [b for b in self.books.values() if b.family_id == family_id]
		return items[offset:offset+limit]

	async def find_all_by_shelf_ids(self, shelf_ids: list[UUID]) -> list[OwnedBook]:
		return [b for b in self.books.values() if b.shelf_id in shelf_ids]

	async def exists_by_bibliographic_record_id(self, record_id: UUID) -> bool:
		return any(b.bibliographic_record_id == record_id for b in self.books.values())

	async def delete(self, book_id: UUID) -> None:
		self.books.pop(book_id, None)


class MockSectionRepository(SectionRepository):
	def __init__(self):
		self.sections = {}

	async def save(self, section: Section) -> Section:
		self.sections[section.id] = section
		return section

	async def find_by_id(self, section_id: UUID) -> Section | None:
		return self.sections.get(section_id)

	async def find_all_by_family(self, family_id: UUID, bookcase_id: UUID | None = None, limit: int = 50, offset: int = 0) -> list[Section]:
		items = [s for s in self.sections.values() if s.family_id == family_id]
		if bookcase_id:
			items = [s for s in items if s.bookcase_id == bookcase_id]
		return items[offset:offset+limit]

	async def find_all_by_bookcase(self, bookcase_id: UUID, limit: int = 50, offset: int = 0) -> list[Section]:
		items = [s for s in self.sections.values() if s.bookcase_id == bookcase_id]
		return items[offset:offset+limit]

	async def delete(self, section_id: UUID) -> None:
		self.sections.pop(section_id, None)


class MockShelfRepository(ShelfRepository):
	def __init__(self):
		self.shelves = {}

	async def save(self, shelf: Shelf) -> Shelf:
		self.shelves[shelf.id] = shelf
		return shelf

	async def find_by_id(self, shelf_id: UUID) -> Shelf | None:
		return self.shelves.get(shelf_id)

	async def find_all_by_family(self, family_id: UUID, section_id: UUID | None = None, limit: int = 50, offset: int = 0) -> list[Shelf]:
		items = [s for s in self.shelves.values() if s.family_id == family_id]
		if section_id:
			items = [s for s in items if s.section_id == section_id]
		return items[offset:offset+limit]

	async def find_all_by_section(self, section_id: UUID, limit: int = 50, offset: int = 0) -> list[Shelf]:
		items = [s for s in self.shelves.values() if s.section_id == section_id]
		return items[offset:offset+limit]

	async def delete(self, shelf_id: UUID) -> None:
		self.shelves.pop(shelf_id, None)


class MockBookHistoryRepository(BookHistoryRepository):
	def __init__(self):
		self.history = {}

	async def save(self, entry) -> None:
		self.history[uuid4()] = entry

	async def find_by_book_id(self, book_id: UUID, limit: int = 50, offset: int = 0) -> list:
		items = [e for e in self.history.values() if e.owned_book_id == book_id]
		return items[offset:offset+limit]


class MockIsbnLookupCacheRepository(IsbnLookupCacheRepository):
	def __init__(self):
		self.cache = {}

	async def save(self, entry) -> None:
		self.cache[entry.isbn] = entry

	async def find_by_isbn(self, isbn: str):
		return self.cache.get(isbn)


@pytest.fixture
def test_family_id() -> UUID:
	return uuid4()


@pytest.fixture
def test_user_id() -> UUID:
	return uuid4()


@pytest.fixture
def room_repo() -> RoomRepository:
	return MockRoomRepository()


@pytest.fixture
def bookcase_repo() -> BookcaseRepository:
	return MockBookcaseRepository()


@pytest.fixture
def section_repo() -> SectionRepository:
	return MockSectionRepository()


@pytest.fixture
def shelf_repo() -> ShelfRepository:
	return MockShelfRepository()


@pytest.fixture
def record_repo() -> BibliographicRecordRepository:
	return MockBibliographicRecordRepository()


@pytest.fixture
def book_repo() -> OwnedBookRepository:
	return MockOwnedBookRepository()


@pytest.fixture
def history_repo() -> BookHistoryRepository:
	return MockBookHistoryRepository()


@pytest.fixture
def cache_repo() -> IsbnLookupCacheRepository:
	return MockIsbnLookupCacheRepository()
