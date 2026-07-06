from datetime import datetime
from uuid import UUID, uuid4

import pytest

from app.domain.entities import (
	BibliographicRecord,
	Bookcase,
	BookLoan,
	BookRating,
	BookRead,
	OwnedBook,
	RemovedMember,
	Room,
	Section,
	Shelf,
	WishlistItem,
)
from app.domain.repositories import (
	BibliographicRecordRepository,
	BookcaseRepository,
	BookHistoryRepository,
	BookLoanRepository,
	BookRatingRepository,
	BookReadRepository,
	IsbnLookupCacheRepository,
	OwnedBookRepository,
	RemovedMemberRepository,
	RoomRepository,
	SectionRepository,
	ShelfRepository,
	WishlistRepository,
)


class MockRoomRepository(RoomRepository):
	def __init__(self):
		self.rooms = {}

	async def save(self, room: Room) -> Room:
		self.rooms[room.id] = room
		return room

	async def find_by_id(self, room_id: UUID) -> Room | None:
		return self.rooms.get(room_id)

	async def find_all_by_library(self, library_id: UUID, limit: int = 50, offset: int = 0) -> list[Room]:
		return [r for r in self.rooms.values() if r.library_id == library_id][offset:offset+limit]

	async def find_by_name(self, library_id: UUID, name: str) -> Room | None:
		return next((r for r in self.rooms.values() if r.library_id == library_id and r.name == name), None)

	async def delete(self, room_id: UUID) -> None:
		self.rooms.pop(room_id, None)

	async def delete_all_by_library(self, library_id: UUID) -> None:
		self.rooms = {k: v for k, v in self.rooms.items() if v.library_id != library_id}


class MockBookcaseRepository(BookcaseRepository):
	def __init__(self):
		self.bookcases = {}

	async def save(self, bookcase: Bookcase) -> Bookcase:
		self.bookcases[bookcase.id] = bookcase
		return bookcase

	async def find_by_id(self, bookcase_id: UUID) -> Bookcase | None:
		return self.bookcases.get(bookcase_id)

	async def find_all_by_library(
		self, library_id: UUID, room_id: UUID | None = None, limit: int = 50, offset: int = 0
	) -> list[Bookcase]:
		items = [b for b in self.bookcases.values() if b.library_id == library_id]
		if room_id:
			items = [b for b in items if b.room_id == room_id]
		return items[offset:offset+limit]

	async def find_by_name(self, room_id: UUID, name: str) -> Bookcase | None:
		return next((b for b in self.bookcases.values() if b.room_id == room_id and b.name == name), None)

	async def delete(self, bookcase_id: UUID) -> None:
		self.bookcases.pop(bookcase_id, None)

	async def delete_all_by_library(self, library_id: UUID) -> None:
		self.bookcases = {k: v for k, v in self.bookcases.items() if v.library_id != library_id}


class MockBibliographicRecordRepository(BibliographicRecordRepository):
	def __init__(self):
		self.records = {}

	async def save(self, record: BibliographicRecord) -> BibliographicRecord:
		self.records[record.id] = record
		return record

	async def find_by_id(self, record_id: UUID) -> BibliographicRecord | None:
		return self.records.get(record_id)

	async def find_by_isbn(self, library_id: UUID, isbn: str) -> BibliographicRecord | None:
		for r in self.records.values():
			if r.library_id == library_id and r.isbn == isbn:
				return r
		return None

	async def find_by_title_author(
		self, library_id: UUID, title: str, main_author: str | None
	) -> BibliographicRecord | None:
		for r in self.records.values():
			if r.library_id == library_id and r.title == title and r.main_author == main_author:
				return r
		return None

	async def find_all_by_library(
		self,
		library_id: UUID,
		q: str | None = None,
		genre: str | None = None,
		limit: int = 50,
		offset: int = 0,
	) -> list[BibliographicRecord]:
		items = [r for r in self.records.values() if r.library_id == library_id]
		if genre:
			items = [r for r in items if r.genre == genre]
		if q:
			items = [r for r in items if q.lower() in r.title.lower()]
		return items[offset:offset+limit]

	async def count_genres(self, library_id: UUID) -> list[tuple[str, int]]:
		counts: dict[str, int] = {}
		for r in self.records.values():
			if r.library_id == library_id and r.genre:
				counts[r.genre] = counts.get(r.genre, 0) + 1
		return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)

	async def find_all_by_ids(self, ids: list[UUID]) -> list[BibliographicRecord]:
		return [self.records[id] for id in ids if id in self.records]

	async def delete(self, record_id: UUID) -> None:
		self.records.pop(record_id, None)

	async def delete_all_by_library(self, library_id: UUID) -> None:
		self.records = {k: v for k, v in self.records.items() if v.library_id != library_id}


class MockOwnedBookRepository(OwnedBookRepository):
	def __init__(self):
		self.books = {}

	async def save(self, book: OwnedBook) -> OwnedBook:
		self.books[book.id] = book
		return book

	async def find_by_id(self, book_id: UUID) -> OwnedBook | None:
		return self.books.get(book_id)

	async def find_all_by_library(self, library_id: UUID, limit: int = 50, offset: int = 0) -> list[OwnedBook]:
		items = [b for b in self.books.values() if b.library_id == library_id]
		return items[offset:offset+limit]

	async def find_all_by_shelf_ids(self, shelf_ids: list[UUID]) -> list[OwnedBook]:
		return [b for b in self.books.values() if b.shelf_id in shelf_ids]

	async def find_by_ids(self, book_ids: list[UUID]) -> list[OwnedBook]:
		return [b for b in self.books.values() if b.id in set(book_ids)]

	async def exists_by_bibliographic_record_id(self, record_id: UUID) -> bool:
		return any(b.bibliographic_record_id == record_id for b in self.books.values())

	async def find_duplicate(
		self, library_id: UUID, bibliographic_record_id: UUID,
		room_id, bookcase_id, section_id, shelf_id, shelf_position
	) -> OwnedBook | None:
		return next(
			(
				b for b in self.books.values()
				if b.library_id == library_id
				and b.bibliographic_record_id == bibliographic_record_id
				and b.room_id == room_id
				and b.bookcase_id == bookcase_id
				and b.section_id == section_id
				and b.shelf_id == shelf_id
				and b.shelf_position == shelf_position
			),
			None,
		)

	async def find_one_by_record(self, bibliographic_record_id: UUID) -> OwnedBook | None:
		return next(
			(b for b in self.books.values() if b.bibliographic_record_id == bibliographic_record_id),
			None,
		)

	async def delete(self, book_id: UUID) -> None:
		self.books.pop(book_id, None)

	async def delete_by_ids(self, book_ids: list[UUID]) -> None:
		ids = set(book_ids)
		self.books = {k: v for k, v in self.books.items() if k not in ids}

	async def delete_all_by_library(self, library_id: UUID) -> None:
		self.books = {k: v for k, v in self.books.items() if v.library_id != library_id}


class MockSectionRepository(SectionRepository):
	def __init__(self):
		self.sections = {}

	async def save(self, section: Section) -> Section:
		self.sections[section.id] = section
		return section

	async def find_by_id(self, section_id: UUID) -> Section | None:
		return self.sections.get(section_id)

	async def find_all_by_library(
		self, library_id: UUID, bookcase_id: UUID | None = None, limit: int = 50, offset: int = 0
	) -> list[Section]:
		items = [s for s in self.sections.values() if s.library_id == library_id]
		if bookcase_id:
			items = [s for s in items if s.bookcase_id == bookcase_id]
		return items[offset:offset+limit]

	async def find_all_by_bookcase(self, bookcase_id: UUID, limit: int = 50, offset: int = 0) -> list[Section]:
		items = [s for s in self.sections.values() if s.bookcase_id == bookcase_id]
		return items[offset:offset+limit]

	async def find_by_index(self, bookcase_id: UUID, section_index: int) -> Section | None:
		return next(
			(
				s
				for s in self.sections.values()
				if s.bookcase_id == bookcase_id and s.section_index == section_index
			),
			None,
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

	async def find_all_by_library(
		self, library_id: UUID, section_id: UUID | None = None, limit: int = 50, offset: int = 0
	) -> list[Shelf]:
		items = [s for s in self.shelves.values() if s.library_id == library_id]
		if section_id:
			items = [s for s in items if s.section_id == section_id]
		return items[offset:offset+limit]

	async def find_all_by_section(self, section_id: UUID, limit: int = 50, offset: int = 0) -> list[Shelf]:
		items = [s for s in self.shelves.values() if s.section_id == section_id]
		return items[offset:offset+limit]

	async def find_all_by_section_ids(self, section_ids: list[UUID]) -> list[Shelf]:
		return [s for s in self.shelves.values() if s.section_id in section_ids]

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

	async def find_all_by_library(self, library_id: UUID) -> list:
		# This mock doesn't model the owned_book -> library join the real
		# repository does; it just returns everything stored. Tests that need
		# real library-boundary behavior should filter the input fixtures instead.
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

	async def delete_by_owned_book_ids(self, owned_book_ids: list[UUID]) -> None:
		ids = set(owned_book_ids)
		self.history = {k: v for k, v in self.history.items() if v.owned_book_id not in ids}


class MockBookReadRepository(BookReadRepository):
	def __init__(self):
		self.reads = {}

	async def add(self, owned_book_id: UUID, user_id: UUID, read_at: datetime | None = None) -> BookRead:
		for r in self.reads.values():
			if r.owned_book_id == owned_book_id and r.user_id == user_id:
				if read_at is not None:
					r.read_at = read_at
				return r
		kwargs = {"read_at": read_at} if read_at is not None else {}
		read = BookRead(owned_book_id=owned_book_id, user_id=user_id, **kwargs)
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

	async def list_by_library(self, library_id: UUID) -> list[BookRead]:
		# Like MockBookHistoryRepository, this mock doesn't model the
		# owned_book -> library join; it returns everything stored.
		return list(self.reads.values())

	async def is_read(self, owned_book_id: UUID, user_id: UUID) -> bool:
		return any(r.owned_book_id == owned_book_id and r.user_id == user_id for r in self.reads.values())

	async def list_read_book_ids(self, owned_book_ids: list[UUID], user_id: UUID) -> set[UUID]:
		ids = set(owned_book_ids)
		return {r.owned_book_id for r in self.reads.values() if r.user_id == user_id and r.owned_book_id in ids}

	async def restore(self, book_read: BookRead) -> BookRead:
		existing = next(
			(
				r
				for r in self.reads.values()
				if r.id == book_read.id
				or (r.owned_book_id == book_read.owned_book_id and r.user_id == book_read.user_id)
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

	async def list_active_by_library(self, library_id: UUID) -> list[BookLoan]:
		return [loan for loan in self.loans.values() if loan.returned_at is None]

	async def list_due_for_reminder(self, due_before) -> list[BookLoan]:
		return [
			loan for loan in self.loans.values()
			if loan.returned_at is None
			and loan.reminder_sent_at is None
			and loan.due_date is not None
			and loan.due_date <= due_before
		]

	async def mark_reminder_sent(self, loan_id: UUID, sent_at) -> None:
		if loan_id in self.loans:
			self.loans[loan_id].reminder_sent_at = sent_at

	async def find_all_by_library(self, library_id: UUID) -> list[BookLoan]:
		# Like MockBookHistoryRepository, this mock doesn't model the
		# owned_book -> library join; it returns everything stored.
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


class MockWishlistRepository(WishlistRepository):
	def __init__(self) -> None:
		self.items: dict[UUID, WishlistItem] = {}

	async def get(self, item_id: UUID, library_id: UUID) -> WishlistItem | None:
		item = self.items.get(item_id)
		return item if item and item.library_id == library_id else None

	async def list_by_library(self, library_id: UUID) -> list[WishlistItem]:
		return [i for i in self.items.values() if i.library_id == library_id]

	async def list_by_user(self, user_id: UUID) -> list[WishlistItem]:
		return [i for i in self.items.values() if i.user_id == user_id]

	async def add(self, item: WishlistItem) -> WishlistItem:
		self.items[item.id] = item
		return item

	async def delete(self, item_id: UUID, library_id: UUID) -> None:
		self.items.pop(item_id, None)

	async def exists_for_user_and_record(self, user_id: UUID, record_id: UUID) -> bool:
		return any(
			i.user_id == user_id and i.bibliographic_record_id == record_id
			for i in self.items.values()
		)

	async def restore(self, item: WishlistItem) -> WishlistItem:
		existing = next(
			(
				i for i in self.items.values()
				if i.user_id == item.user_id and i.bibliographic_record_id == item.bibliographic_record_id
			),
			None,
		)
		if existing:
			return existing
		self.items[item.id] = item
		return item


class MockBookRatingRepository(BookRatingRepository):
	def __init__(self) -> None:
		self.ratings: dict[UUID, BookRating] = {}

	async def add(self, rating: BookRating) -> BookRating:
		self.ratings[rating.id] = rating
		return rating

	async def save(self, rating: BookRating) -> BookRating:
		self.ratings[rating.id] = rating
		return rating

	async def find_by_id(self, rating_id: UUID) -> BookRating | None:
		return self.ratings.get(rating_id)

	async def find_by_book_and_user(self, owned_book_id: UUID, user_id: UUID) -> BookRating | None:
		return next(
			(r for r in self.ratings.values() if r.owned_book_id == owned_book_id and r.user_id == user_id), None
		)

	async def list_by_book(self, owned_book_id: UUID) -> list[BookRating]:
		return [r for r in self.ratings.values() if r.owned_book_id == owned_book_id]

	async def list_by_library(self, library_id: UUID) -> list[BookRating]:
		# Like MockBookHistoryRepository, this mock doesn't model the
		# owned_book -> library join; it returns everything stored.
		return list(self.ratings.values())

	async def delete(self, rating: BookRating) -> None:
		self.ratings.pop(rating.id, None)

	async def restore(self, rating: BookRating) -> BookRating:
		existing = next(
			(
				r for r in self.ratings.values()
				if r.owned_book_id == rating.owned_book_id and r.user_id == rating.user_id
			),
			None,
		)
		if existing:
			return existing
		self.ratings[rating.id] = rating
		return rating


class MockRemovedMemberRepository(RemovedMemberRepository):
	def __init__(self):
		self.members = {}

	async def save(self, member: RemovedMember) -> RemovedMember:
		self.members[member.id] = member
		return member

	async def find_all_by_library(self, library_id: UUID) -> list[RemovedMember]:
		return [m for m in self.members.values() if m.library_id == library_id]

	async def delete_all_by_library(self, library_id: UUID) -> None:
		self.members = {k: v for k, v in self.members.items() if v.library_id != library_id}

	async def delete_expired(self, older_than) -> int:
		expired = [k for k, v in self.members.items() if v.removed_at < older_than]
		for k in expired:
			del self.members[k]
		return len(expired)


@pytest.fixture
def test_library_id() -> UUID:
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


@pytest.fixture
def removed_member_repo() -> RemovedMemberRepository:
	return MockRemovedMemberRepository()


@pytest.fixture
def wishlist_repo() -> WishlistRepository:
	return MockWishlistRepository()


@pytest.fixture
def book_rating_repo() -> BookRatingRepository:
	return MockBookRatingRepository()
