import pytest
from uuid import uuid4, UUID
from datetime import datetime

from app.domain.entities import Room, Bookcase, Section, Shelf, BibliographicRecord, OwnedBook, BookRead, BookLoan
from app.domain.repositories import (
	RoomRepository,
	BookcaseRepository,
	SectionRepository,
	ShelfRepository,
	BibliographicRecordRepository,
	OwnedBookRepository,
	BookHistoryRepository,
	BookReadRepository,
	BookLoanRepository,
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

	async def find_by_name(self, family_id: UUID, name: str) -> Room | None:
		return next((r for r in self.rooms.values() if r.family_id == family_id and r.name == name), None)

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

	async def find_by_name(self, room_id: UUID, name: str) -> Bookcase | None:
		return next((b for b in self.bookcases.values() if b.room_id == room_id and b.name == name), None)

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

	async def find_by_title_author(self, family_id: UUID, title: str, main_author: str | None) -> BibliographicRecord | None:
		for r in self.records.values():
			if r.family_id == family_id and r.title == title and r.main_author == main_author:
				return r
		return None

	async def find_all_by_family(self, family_id: UUID, q: str | None = None, genre: str | None = None, limit: int = 50, offset: int = 0) -> list[BibliographicRecord]:
		items = [r for r in self.records.values() if r.family_id == family_id]
		if genre:
			items = [r for r in items if r.genre == genre]
		if q:
			items = [r for r in items if q.lower() in r.title.lower()]
		return items[offset:offset+limit]

	async def count_genres(self, family_id: UUID) -> list[tuple[str, int]]:
		counts: dict[str, int] = {}
		for r in self.records.values():
			if r.family_id == family_id and r.genre:
				counts[r.genre] = counts.get(r.genre, 0) + 1
		return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)

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

	async def find_duplicate(
		self, family_id: UUID, bibliographic_record_id: UUID, room_id, bookcase_id, section_id, shelf_id, shelf_position
	) -> OwnedBook | None:
		return next(
			(
				b for b in self.books.values()
				if b.family_id == family_id
				and b.bibliographic_record_id == bibliographic_record_id
				and b.room_id == room_id
				and b.bookcase_id == bookcase_id
				and b.section_id == section_id
				and b.shelf_id == shelf_id
				and b.shelf_position == shelf_position
			),
			None,
		)

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

	async def find_by_index(self, bookcase_id: UUID, section_index: int) -> Section | None:
		return next(
			(s for s in self.sections.values() if s.bookcase_id == bookcase_id and s.section_index == section_index), None
		)

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

	async def find_by_index(self, section_id: UUID, shelf_index: int) -> Shelf | None:
		return next(
			(s for s in self.shelves.values() if s.section_id == section_id and s.shelf_index == shelf_index), None
		)

	async def delete(self, shelf_id: UUID) -> None:
		self.shelves.pop(shelf_id, None)


class MockBookHistoryRepository(BookHistoryRepository):
	def __init__(self):
		self.history = {}

	async def save(self, entry) -> None:
		self.history[uuid4()] = entry

	async def find_by_book(self, book_id: UUID, limit: int = 50, offset: int = 0) -> list:
		items = [e for e in self.history.values() if e.owned_book_id == book_id]
		return items[offset:offset+limit]

	async def find_all_by_family(self, family_id: UUID) -> list:
		# This mock doesn't model the owned_book -> family join the real
		# repository does; it just returns everything stored. Tests that need
		# real family-boundary behavior should filter the input fixtures instead.
		return list(self.history.values())

	async def restore(self, history):
		existing = next(
			(
				h for h in self.history.values()
				if h.owned_book_id == history.owned_book_id
				and h.event_type == history.event_type
				and h.changed_by == history.changed_by
				and h.created_at == history.created_at
			),
			None,
		)
		if existing:
			return existing
		self.history[history.id] = history
		return history


class MockBookReadRepository(BookReadRepository):
	def __init__(self):
		self.reads = {}

	async def add(self, owned_book_id: UUID, user_id: UUID) -> BookRead:
		for r in self.reads.values():
			if r.owned_book_id == owned_book_id and r.user_id == user_id:
				return r
		read = BookRead(owned_book_id=owned_book_id, user_id=user_id)
		self.reads[read.id] = read
		return read

	async def remove(self, owned_book_id: UUID, user_id: UUID) -> None:
		match = next(
			(r for r in self.reads.values() if r.owned_book_id == owned_book_id and r.user_id == user_id), None
		)
		if match:
			self.reads.pop(match.id, None)

	async def list_by_book(self, owned_book_id: UUID) -> list[BookRead]:
		return [r for r in self.reads.values() if r.owned_book_id == owned_book_id]

	async def list_by_family(self, family_id: UUID) -> list[BookRead]:
		# Like MockBookHistoryRepository, this mock doesn't model the
		# owned_book -> family join; it returns everything stored.
		return list(self.reads.values())

	async def restore(self, book_read: BookRead) -> BookRead:
		existing = next(
			(
				r for r in self.reads.values()
				if r.id == book_read.id or (r.owned_book_id == book_read.owned_book_id and r.user_id == book_read.user_id)
			),
			None,
		)
		if existing:
			return existing
		self.reads[book_read.id] = book_read
		return book_read


class MockBookLoanRepository(BookLoanRepository):
	def __init__(self):
		self.loans = {}

	async def add(self, loan: BookLoan) -> BookLoan:
		self.loans[loan.id] = loan
		return loan

	async def mark_returned(self, loan_id: UUID, returned_at) -> None:
		if loan_id in self.loans:
			self.loans[loan_id].returned_at = returned_at

	async def get_active_for_book(self, owned_book_id: UUID):
		return next(
			(loan for loan in self.loans.values() if loan.owned_book_id == owned_book_id and loan.returned_at is None),
			None,
		)

	async def list_by_book(self, owned_book_id: UUID) -> list[BookLoan]:
		return [loan for loan in self.loans.values() if loan.owned_book_id == owned_book_id]

	async def list_active_by_family(self, family_id: UUID) -> list[BookLoan]:
		return [loan for loan in self.loans.values() if loan.returned_at is None]

	async def find_all_by_family(self, family_id: UUID) -> list[BookLoan]:
		# Like MockBookHistoryRepository, this mock doesn't model the
		# owned_book -> family join; it returns everything stored.
		return list(self.loans.values())

	async def restore(self, loan: BookLoan) -> BookLoan:
		existing = next(
			(
				lo for lo in self.loans.values()
				if lo.owned_book_id == loan.owned_book_id
				and lo.borrower_name == loan.borrower_name
				and lo.loaned_at == loan.loaned_at
			),
			None,
		)
		if existing:
			return existing
		self.loans[loan.id] = loan
		return loan


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
def book_read_repo() -> BookReadRepository:
	return MockBookReadRepository()


@pytest.fixture
def book_loan_repo() -> BookLoanRepository:
	return MockBookLoanRepository()


@pytest.fixture
def cache_repo() -> IsbnLookupCacheRepository:
	return MockIsbnLookupCacheRepository()
