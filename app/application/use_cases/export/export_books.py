from dataclasses import dataclass, field
from uuid import UUID

from app.domain.entities import (
	BibliographicRecord,
	Bookcase,
	BookLoan,
	BookRead,
	OwnedBook,
	Room,
	Section,
	Shelf,
)
from app.domain.repositories import (
	BibliographicRecordRepository,
	BookcaseRepository,
	BookLoanRepository,
	BookReadRepository,
	OwnedBookRepository,
	RoomRepository,
	SectionRepository,
	ShelfRepository,
)

_LOCATION_FETCH_LIMIT = 9999


@dataclass
class ExportBookItem:
	book: OwnedBook
	record: BibliographicRecord | None
	room: Room | None = None
	bookcase: Bookcase | None = None
	section: Section | None = None
	shelf: Shelf | None = None
	readers: list[BookRead] = field(default_factory=list)
	active_loan: BookLoan | None = None


class ExportBooksUseCase:
	def __init__(
		self,
		book_repo: OwnedBookRepository,
		record_repo: BibliographicRecordRepository,
		room_repo: RoomRepository,
		bookcase_repo: BookcaseRepository,
		section_repo: SectionRepository,
		shelf_repo: ShelfRepository,
		book_read_repo: BookReadRepository,
		book_loan_repo: BookLoanRepository,
	) -> None:
		self._book_repo = book_repo
		self._record_repo = record_repo
		self._room_repo = room_repo
		self._bookcase_repo = bookcase_repo
		self._section_repo = section_repo
		self._shelf_repo = shelf_repo
		self._book_read_repo = book_read_repo
		self._book_loan_repo = book_loan_repo

	async def execute(self, family_id: UUID, limit: int, offset: int) -> list[ExportBookItem]:
		books = await self._book_repo.find_all_by_family(family_id, limit=limit, offset=offset)
		if not books:
			return []

		# Bibliographic records
		record_map = {
			r.id: r
			for r in await self._record_repo.find_all_by_ids(
				[b.bibliographic_record_id for b in books]
			)
		}

		# Location maps — one query per type, then joined in memory
		room_map = {
			r.id: r
			for r in await self._room_repo.find_all_by_family(
				family_id, limit=_LOCATION_FETCH_LIMIT
			)
		}
		bookcase_map = {
			bc.id: bc
			for bc in await self._bookcase_repo.find_all_by_family(
				family_id, limit=_LOCATION_FETCH_LIMIT
			)
		}
		section_map = {
			s.id: s
			for s in await self._section_repo.find_all_by_family(
				family_id, limit=_LOCATION_FETCH_LIMIT
			)
		}
		shelf_map = {
			sh.id: sh
			for sh in await self._shelf_repo.find_all_by_family(
				family_id, limit=_LOCATION_FETCH_LIMIT
			)
		}

		# Reads: family-wide fetch, grouped by book
		reads_by_book: dict[UUID, list[BookRead]] = {}
		for read in await self._book_read_repo.list_by_family(family_id):
			reads_by_book.setdefault(read.owned_book_id, []).append(read)

		# Active loans: family-wide fetch, keyed by book
		loan_by_book: dict[UUID, BookLoan] = {
			loan.owned_book_id: loan
			for loan in await self._book_loan_repo.list_active_by_family(family_id)
		}

		return [
			ExportBookItem(
				book=book,
				record=record_map.get(book.bibliographic_record_id),
				room=room_map.get(book.room_id) if book.room_id else None,
				bookcase=bookcase_map.get(book.bookcase_id) if book.bookcase_id else None,
				section=section_map.get(book.section_id) if book.section_id else None,
				shelf=shelf_map.get(book.shelf_id) if book.shelf_id else None,
				readers=reads_by_book.get(book.id, []),
				active_loan=loan_by_book.get(book.id),
			)
			for book in books
		]
