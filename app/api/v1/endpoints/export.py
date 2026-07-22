import csv
from datetime import UTC, datetime
from io import StringIO
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.dependencies import (
	get_bibliographic_record_repository,
	get_book_history_repository,
	get_book_loan_repository,
	get_book_read_repository,
	get_bookcase_repository,
	get_current_user_payload,
	get_owned_book_repository,
	get_removed_member_repository,
	get_room_repository,
	get_section_repository,
	get_shelf_repository,
	get_wishlist_repository,
	require_role,
)
from app.api.v1.schemas.export_schemas import (
	BibliographicRecordExportItem,
	BookcaseExportItem,
	BookHistoryExportItem,
	BookLoanExportItem,
	BookReadExportItem,
	FullLibraryExportResponse,
	OwnedBookExportItem,
	RemovedMemberExportItem,
	RoomExportItem,
	SectionExportItem,
	ShelfExportItem,
	WishlistItemExportItem,
)
from app.application.use_cases import ExportBooksUseCase, ExportFullLibraryUseCase
from app.application.use_cases.export.export_books import ExportBookItem
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

router = APIRouter(tags=["export"])

# Formula-injection prefixes (OWASP CSV Injection / CWE-1236): any of these
# leading characters makes Excel/LibreOffice/Sheets interpret the cell as a
# formula instead of literal text when the export is later opened — a
# malicious book title like `=cmd|'/C calc'!A1` executes on whoever opens the
# CSV. Prefixing with a single quote forces spreadsheet apps to render it as
# plain text without changing the value a non-spreadsheet CSV consumer sees.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _sanitize_csv_value(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


_CSV_FIELDS = [
	# Book identity
	"book_id", "library_id", "owner_id", "current_reader_id",
	# Status & acquisition
	"reading_status", "condition", "source", "purchase_date", "purchase_price",
	# Tags, notes, duplicates
	"tags", "notes", "is_intentional_duplicate", "duplicate_notes",
	# Bibliographic record
	"record_id", "title", "main_author", "other_authors",
	"isbn", "publisher", "publication_year", "book_language", "genre",
	"cover_url", "record_notes",
	# Physical location (IDs + human-readable names)
	"room_id", "room_name",
	"bookcase_id", "bookcase_name",
	"section_id", "section_index", "section_label",
	"shelf_id", "shelf_index", "shelf_notes", "shelf_position", "position_description",
	# Who has read it (pipe-separated "user_id:read_at" pairs)
	"readers",
	# Active loan
	"active_loan_borrower", "active_loan_loaned_at", "active_loan_due_date",
	# Timestamps
	"created_at", "updated_at",
]


def _build_use_case(
	book_repo: OwnedBookRepository,
	record_repo: BibliographicRecordRepository,
	room_repo: RoomRepository,
	bookcase_repo: BookcaseRepository,
	section_repo: SectionRepository,
	shelf_repo: ShelfRepository,
	book_read_repo: BookReadRepository,
	book_loan_repo: BookLoanRepository,
) -> ExportBooksUseCase:
	return ExportBooksUseCase(
		book_repo=book_repo,
		record_repo=record_repo,
		room_repo=room_repo,
		bookcase_repo=bookcase_repo,
		section_repo=section_repo,
		shelf_repo=shelf_repo,
		book_read_repo=book_read_repo,
		book_loan_repo=book_loan_repo,
	)


def _csv_row(item: ExportBookItem) -> dict[str, Any]:
	b = item.book
	r = item.record

	readers_str = "|".join(
		f"{read.user_id}:{read.read_at.isoformat()}"
		for read in sorted(item.readers, key=lambda x: x.read_at)
	)

	loan = item.active_loan

	return {
		"book_id": str(b.id),
		"library_id": str(b.library_id),
		"owner_id": str(b.owner_id) if b.owner_id else None,
		"current_reader_id": str(b.current_reader_id) if b.current_reader_id else None,
		"reading_status": b.reading_status.value,
		"condition": b.condition.value if b.condition else None,
		"source": b.source.value if b.source else None,
		"purchase_date": b.purchase_date.isoformat() if b.purchase_date else None,
		"purchase_price": str(b.purchase_price) if b.purchase_price is not None else None,
		"tags": "|".join(b.tags),
		"notes": b.notes,
		"is_intentional_duplicate": b.is_intentional_duplicate,
		"duplicate_notes": b.duplicate_notes,
		"record_id": str(r.id) if r else None,
		"title": r.title if r else None,
		"main_author": r.main_author if r else None,
		"other_authors": "|".join(r.other_authors) if r else None,
		"isbn": r.isbn if r else None,
		"publisher": r.publisher if r else None,
		"publication_year": r.publication_year if r else None,
		"book_language": r.language if r else None,
		"genre": r.genre if r else None,
		"cover_url": r.cover_url if r else None,
		"record_notes": r.notes if r else None,
		"room_id": str(b.room_id) if b.room_id else None,
		"room_name": item.room.name if item.room else None,
		"bookcase_id": str(b.bookcase_id) if b.bookcase_id else None,
		"bookcase_name": item.bookcase.name if item.bookcase else None,
		"section_id": str(b.section_id) if b.section_id else None,
		"section_index": item.section.section_index if item.section else None,
		"section_label": item.section.label if item.section else None,
		"shelf_id": str(b.shelf_id) if b.shelf_id else None,
		"shelf_index": item.shelf.shelf_index if item.shelf else None,
		"shelf_notes": item.shelf.notes if item.shelf else None,
		"shelf_position": b.shelf_position,
		"position_description": b.position_description,
		"readers": readers_str,
		"active_loan_borrower": loan.borrower_name if loan else None,
		"active_loan_loaned_at": loan.loaned_at.isoformat() if loan else None,
		"active_loan_due_date": loan.due_date.isoformat() if loan and loan.due_date else None,
		"created_at": b.created_at.isoformat(),
		"updated_at": b.updated_at.isoformat(),
	}


def _json_book(item: ExportBookItem) -> dict[str, Any]:
	b = item.book
	r = item.record
	loan = item.active_loan

	return {
		"id": str(b.id),
		"record": {
			"id": str(r.id),
			"title": r.title,
			"main_author": r.main_author,
			"other_authors": r.other_authors,
			"isbn": r.isbn,
			"publisher": r.publisher,
			"publication_year": r.publication_year,
			"language": r.language,
			"genre": r.genre,
			"cover_url": r.cover_url,
			"notes": r.notes,
		} if r else None,
		"reading_status": b.reading_status.value,
		"condition": b.condition.value if b.condition else None,
		"source": b.source.value if b.source else None,
		"purchase_date": b.purchase_date.isoformat() if b.purchase_date else None,
		"purchase_price": str(b.purchase_price) if b.purchase_price is not None else None,
		"owner_id": str(b.owner_id) if b.owner_id else None,
		"current_reader_id": str(b.current_reader_id) if b.current_reader_id else None,
		"tags": b.tags,
		"notes": b.notes,
		"is_intentional_duplicate": b.is_intentional_duplicate,
		"duplicate_notes": b.duplicate_notes,
		"location": {
			"room_id": str(b.room_id) if b.room_id else None,
			"room_name": item.room.name if item.room else None,
			"bookcase_id": str(b.bookcase_id) if b.bookcase_id else None,
			"bookcase_name": item.bookcase.name if item.bookcase else None,
			"section_id": str(b.section_id) if b.section_id else None,
			"section_index": item.section.section_index if item.section else None,
			"section_label": item.section.label if item.section else None,
			"shelf_id": str(b.shelf_id) if b.shelf_id else None,
			"shelf_index": item.shelf.shelf_index if item.shelf else None,
			"shelf_notes": item.shelf.notes if item.shelf else None,
			"shelf_position": b.shelf_position,
			"position_description": b.position_description,
		},
		"readers": [
			{"user_id": str(read.user_id), "read_at": read.read_at.isoformat()}
			for read in sorted(item.readers, key=lambda x: x.read_at)
		],
		"active_loan": {
			"borrower_name": loan.borrower_name,
			"loaned_at": loan.loaned_at.isoformat(),
			"due_date": loan.due_date.isoformat() if loan.due_date else None,
		} if loan else None,
		"created_at": b.created_at.isoformat(),
		"updated_at": b.updated_at.isoformat(),
	}


@router.get("/books.csv", summary="Export books as CSV")
async def export_books_csv(
	limit: int = Query(default=1000, ge=1, le=10000),
	offset: int = Query(default=0, ge=0),
	payload: dict[str, Any] = Depends(get_current_user_payload),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
	room_repo: RoomRepository = Depends(get_room_repository),
	bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
	section_repo: SectionRepository = Depends(get_section_repository),
	shelf_repo: ShelfRepository = Depends(get_shelf_repository),
	book_read_repo: BookReadRepository = Depends(get_book_read_repository),
	book_loan_repo: BookLoanRepository = Depends(get_book_loan_repository),
) -> StreamingResponse:
	items = await _build_use_case(
		book_repo, record_repo, room_repo, bookcase_repo,
		section_repo, shelf_repo, book_read_repo, book_loan_repo,
	).execute(UUID(payload["library_id"]), limit, offset)

	output = StringIO()
	writer = csv.DictWriter(output, fieldnames=_CSV_FIELDS)
	writer.writeheader()
	for item in items:
		writer.writerow({k: _sanitize_csv_value(v) for k, v in _csv_row(item).items()})

	return StreamingResponse(
		iter([output.getvalue()]),
		media_type="text/csv",
		headers={"Content-Disposition": "attachment; filename=books.csv"},
	)


@router.get("/books.json", summary="Export books as JSON")
async def export_books_json(
	limit: int = Query(default=1000, ge=1, le=10000),
	offset: int = Query(default=0, ge=0),
	payload: dict[str, Any] = Depends(get_current_user_payload),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
	room_repo: RoomRepository = Depends(get_room_repository),
	bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
	section_repo: SectionRepository = Depends(get_section_repository),
	shelf_repo: ShelfRepository = Depends(get_shelf_repository),
	book_read_repo: BookReadRepository = Depends(get_book_read_repository),
	book_loan_repo: BookLoanRepository = Depends(get_book_loan_repository),
) -> dict[str, Any]:
	items = await _build_use_case(
		book_repo, record_repo, room_repo, bookcase_repo,
		section_repo, shelf_repo, book_read_repo, book_loan_repo,
	).execute(UUID(payload["library_id"]), limit, offset)

	return {
		"exported_at": datetime.now(UTC).isoformat(),
		"total": len(items),
		"books": [_json_book(item) for item in items],
	}


@router.get(
	"/full",
	response_model=FullLibraryExportResponse,
	summary="Export the full library for backup",
	description="Everything needed to restore the library elsewhere: the full location "
	"hierarchy (including empty rooms/bookcases), every bibliographic record, every owned "
	"book, every loan (not just active ones), every read, and the audit history. Pair with "
	"GET /v1/users/export (auth-service) for a complete library backup. Requires admin role.",
)
async def export_full_library(
	payload: dict[str, Any] = Depends(require_role("admin")),
	room_repo: RoomRepository = Depends(get_room_repository),
	bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
	section_repo: SectionRepository = Depends(get_section_repository),
	shelf_repo: ShelfRepository = Depends(get_shelf_repository),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	book_read_repo: BookReadRepository = Depends(get_book_read_repository),
	book_loan_repo: BookLoanRepository = Depends(get_book_loan_repository),
	book_history_repo: BookHistoryRepository = Depends(get_book_history_repository),
	removed_member_repo: RemovedMemberRepository = Depends(get_removed_member_repository),
	wishlist_repo: WishlistRepository = Depends(get_wishlist_repository),
) -> FullLibraryExportResponse:
	use_case = ExportFullLibraryUseCase(
		room_repo=room_repo,
		bookcase_repo=bookcase_repo,
		section_repo=section_repo,
		shelf_repo=shelf_repo,
		record_repo=record_repo,
		book_repo=book_repo,
		book_read_repo=book_read_repo,
		book_loan_repo=book_loan_repo,
		book_history_repo=book_history_repo,
		removed_member_repo=removed_member_repo,
		wishlist_repo=wishlist_repo,
	)
	data = await use_case.execute(UUID(payload["library_id"]))

	return FullLibraryExportResponse(
		exported_at=datetime.now(UTC),
		rooms=[RoomExportItem(id=r.id, name=r.name, description=r.description) for r in data.rooms],
		bookcases=[
			BookcaseExportItem(
				id=b.id, room_id=b.room_id, name=b.name, description=b.description,
				type=b.type, notes=b.notes, image_url=b.image_url,
			)
			for b in data.bookcases
		],
		sections=[
			SectionExportItem(id=s.id, bookcase_id=s.bookcase_id, section_index=s.section_index, label=s.label)
			for s in data.sections
		],
		shelves=[
			ShelfExportItem(id=sh.id, section_id=sh.section_id, shelf_index=sh.shelf_index, notes=sh.notes)
			for sh in data.shelves
		],
		bibliographic_records=[
			BibliographicRecordExportItem(
				id=r.id, title=r.title, main_author=r.main_author, other_authors=r.other_authors,
				isbn=r.isbn, publisher=r.publisher, publication_year=r.publication_year,
				language=r.language, genre=r.genre, genre_raw=r.genre_raw, cover_url=r.cover_url,
				notes=r.notes, incipit=r.incipit, incipit_source=r.incipit_source,
				incipit_generated_at=r.incipit_generated_at,
			)
			for r in data.bibliographic_records
		],
		owned_books=[
			OwnedBookExportItem(
				id=b.id, bibliographic_record_id=b.bibliographic_record_id,
				room_id=b.room_id, bookcase_id=b.bookcase_id, section_id=b.section_id, shelf_id=b.shelf_id,
				shelf_position=b.shelf_position, position_description=b.position_description,
				condition=b.condition.value if b.condition else None,
				purchase_date=b.purchase_date, purchase_price=b.purchase_price,
				source=b.source.value if b.source else None,
				reading_status=b.reading_status.value,
				current_reader_id=b.current_reader_id, owner_id=b.owner_id,
				tags=b.tags, notes=b.notes,
				is_intentional_duplicate=b.is_intentional_duplicate, duplicate_notes=b.duplicate_notes,
				created_at=b.created_at, updated_at=b.updated_at,
			)
			for b in data.owned_books
		],
		book_reads=[
			BookReadExportItem(id=r.id, owned_book_id=r.owned_book_id, user_id=r.user_id, read_at=r.read_at)
			for r in data.book_reads
		],
		book_loans=[
			BookLoanExportItem(
				id=loan.id, owned_book_id=loan.owned_book_id, borrower_name=loan.borrower_name,
				borrower_user_id=loan.borrower_user_id,
				loaned_at=loan.loaned_at, due_date=loan.due_date, returned_at=loan.returned_at,
			)
			for loan in data.book_loans
		],
		book_history=[
			BookHistoryExportItem(
				id=h.id, owned_book_id=h.owned_book_id, event_type=h.event_type.value,
				changed_by=h.changed_by, old_data=h.old_data, new_data=h.new_data, created_at=h.created_at,
			)
			for h in data.book_history
		],
		wishlist_items=[
			WishlistItemExportItem(
				id=w.id, user_id=w.user_id, bibliographic_record_id=w.bibliographic_record_id,
				added_at=w.added_at, notes=w.notes, priority=w.priority,
			)
			for w in data.wishlist_items
		],
		removed_members=[
			RemovedMemberExportItem(
				id=m.id, full_name=m.full_name, email=m.email, role=m.role, removed_at=m.removed_at,
			)
			for m in data.removed_members
		],
	)
