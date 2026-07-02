import logging
from dataclasses import dataclass, field
from uuid import UUID

from app.application.services import fetch_all_pages
from app.domain.entities import (
	BibliographicRecord,
	Bookcase,
	BookHistory,
	BookLoan,
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
	BookReadRepository,
	OwnedBookRepository,
	RemovedMemberRepository,
	RoomRepository,
	SectionRepository,
	ShelfRepository,
	WishlistRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class FullLibraryExport:
	rooms: list[Room] = field(default_factory=list)
	bookcases: list[Bookcase] = field(default_factory=list)
	sections: list[Section] = field(default_factory=list)
	shelves: list[Shelf] = field(default_factory=list)
	bibliographic_records: list[BibliographicRecord] = field(default_factory=list)
	owned_books: list[OwnedBook] = field(default_factory=list)
	book_reads: list[BookRead] = field(default_factory=list)
	book_loans: list[BookLoan] = field(default_factory=list)
	book_history: list[BookHistory] = field(default_factory=list)
	wishlist_items: list[WishlistItem] = field(default_factory=list)
	removed_members: list[RemovedMember] = field(default_factory=list)


class ExportFullLibraryUseCase:
	"""Exports every family-owned row needed to fully restore the library
	elsewhere: the location hierarchy (including empty rooms/bookcases/etc,
	unlike the books-only export), every bibliographic record, every owned
	book, every loan (not just active ones), every read, and the full audit
	history. Excludes IsbnLookupCache (a global, non-family cache, not library
	data) on purpose.
	"""

	def __init__(
		self,
		room_repo: RoomRepository,
		bookcase_repo: BookcaseRepository,
		section_repo: SectionRepository,
		shelf_repo: ShelfRepository,
		record_repo: BibliographicRecordRepository,
		book_repo: OwnedBookRepository,
		book_read_repo: BookReadRepository,
		book_loan_repo: BookLoanRepository,
		book_history_repo: BookHistoryRepository,
		removed_member_repo: RemovedMemberRepository,
		wishlist_repo: WishlistRepository,
	) -> None:
		self._room_repo = room_repo
		self._bookcase_repo = bookcase_repo
		self._section_repo = section_repo
		self._shelf_repo = shelf_repo
		self._record_repo = record_repo
		self._book_repo = book_repo
		self._book_read_repo = book_read_repo
		self._book_loan_repo = book_loan_repo
		self._book_history_repo = book_history_repo
		self._removed_member_repo = removed_member_repo
		self._wishlist_repo = wishlist_repo

	async def execute(self, family_id: UUID) -> FullLibraryExport:
		rooms = await fetch_all_pages(
			lambda limit, offset: self._room_repo.find_all_by_family(family_id, limit=limit, offset=offset)
		)
		bookcases = await fetch_all_pages(
			lambda limit, offset: self._bookcase_repo.find_all_by_family(family_id, limit=limit, offset=offset)
		)
		sections = await fetch_all_pages(
			lambda limit, offset: self._section_repo.find_all_by_family(family_id, limit=limit, offset=offset)
		)
		shelves = await fetch_all_pages(
			lambda limit, offset: self._shelf_repo.find_all_by_family(family_id, limit=limit, offset=offset)
		)
		records = await fetch_all_pages(
			lambda limit, offset: self._record_repo.find_all_by_family(family_id, limit=limit, offset=offset)
		)
		books = await fetch_all_pages(
			lambda limit, offset: self._book_repo.find_all_by_family(family_id, limit=limit, offset=offset)
		)

		export = FullLibraryExport(
			rooms=rooms,
			bookcases=bookcases,
			sections=sections,
			shelves=shelves,
			bibliographic_records=records,
			owned_books=books,
			book_reads=await self._book_read_repo.list_by_family(family_id),
			book_loans=await self._book_loan_repo.find_all_by_family(family_id),
			book_history=await self._book_history_repo.find_all_by_family(family_id),
			wishlist_items=await self._wishlist_repo.list_by_family(family_id),
			removed_members=await self._removed_member_repo.find_all_by_family(family_id),
		)
		logger.info(
			"Full library exported for family %s: %d owned book(s), %d bibliographic record(s)",
			family_id,
			len(export.owned_books),
			len(export.bibliographic_records),
		)
		return export
