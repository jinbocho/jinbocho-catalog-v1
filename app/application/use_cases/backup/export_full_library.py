from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from uuid import UUID

from app.domain.entities import (
	BibliographicRecord,
	BookHistory,
	BookLoan,
	BookRead,
	Bookcase,
	OwnedBook,
	Room,
	Section,
	Shelf,
)
from app.domain.repositories import (
	BibliographicRecordRepository,
	BookHistoryRepository,
	BookLoanRepository,
	BookReadRepository,
	BookcaseRepository,
	OwnedBookRepository,
	RoomRepository,
	SectionRepository,
	ShelfRepository,
)

# Internal page size for looping the existing paginated repo methods — not a
# limit on the export itself, the loop continues until every page is exhausted.
_PAGE_SIZE = 500


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

	async def execute(self, family_id: UUID) -> FullLibraryExport:
		rooms = await self._fetch_all(
			lambda limit, offset: self._room_repo.find_all_by_family(family_id, limit=limit, offset=offset)
		)
		bookcases = await self._fetch_all(
			lambda limit, offset: self._bookcase_repo.find_all_by_family(family_id, limit=limit, offset=offset)
		)
		sections = await self._fetch_all(
			lambda limit, offset: self._section_repo.find_all_by_family(family_id, limit=limit, offset=offset)
		)
		shelves = await self._fetch_all(
			lambda limit, offset: self._shelf_repo.find_all_by_family(family_id, limit=limit, offset=offset)
		)
		records = await self._fetch_all(
			lambda limit, offset: self._record_repo.find_all_by_family(family_id, limit=limit, offset=offset)
		)
		books = await self._fetch_all(
			lambda limit, offset: self._book_repo.find_all_by_family(family_id, limit=limit, offset=offset)
		)

		return FullLibraryExport(
			rooms=rooms,
			bookcases=bookcases,
			sections=sections,
			shelves=shelves,
			bibliographic_records=records,
			owned_books=books,
			book_reads=await self._book_read_repo.list_by_family(family_id),
			book_loans=await self._book_loan_repo.find_all_by_family(family_id),
			book_history=await self._book_history_repo.find_all_by_family(family_id),
		)

	@staticmethod
	async def _fetch_all(fetch_page: Callable[[int, int], Awaitable[list]]) -> list:  # type: ignore[type-arg]
		"""Loops a `find_all_by_family(limit, offset)`-shaped repo method until
		a page comes back shorter than the page size — unlike the books-only
		export, this never silently caps out at the first page."""
		results: list = []  # type: ignore[type-arg]
		offset = 0
		while True:
			page = await fetch_page(_PAGE_SIZE, offset)
			results.extend(page)
			if len(page) < _PAGE_SIZE:
				return results
			offset += _PAGE_SIZE
