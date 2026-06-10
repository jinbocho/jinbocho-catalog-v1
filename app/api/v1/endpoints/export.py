import csv
from datetime import datetime, timezone
from io import StringIO
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.dependencies import (
	get_bibliographic_record_repository,
	get_book_loan_repository,
	get_book_read_repository,
	get_bookcase_repository,
	get_current_user_payload,
	get_owned_book_repository,
	get_room_repository,
	get_section_repository,
	get_shelf_repository,
)
from app.application.use_cases import ExportBooksUseCase
from app.application.use_cases.export.export_books import ExportBookItem

router = APIRouter(tags=["export"])

_CSV_FIELDS = [
	# Book identity
	"book_id", "family_id", "owner_id", "current_reader_id",
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


def _ev(v: Any) -> Any:
	"""Return enum .value if present, otherwise the value itself.

	The ORM layer returns raw strings instead of enums until Phase 12 enum
	casting is fixed — this helper survives both cases.
	"""
	return v.value if hasattr(v, "value") else v


def _build_use_case(book_repo, record_repo, room_repo, bookcase_repo, section_repo, shelf_repo, book_read_repo, book_loan_repo):  # type: ignore[no-untyped-def]
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


def _csv_row(item: ExportBookItem) -> dict:  # type: ignore[type-arg]
	b = item.book
	r = item.record

	readers_str = "|".join(
		f"{read.user_id}:{read.read_at.isoformat()}"
		for read in sorted(item.readers, key=lambda x: x.read_at)
	)

	loan = item.active_loan

	return {
		"book_id": str(b.id),
		"family_id": str(b.family_id),
		"owner_id": str(b.owner_id) if b.owner_id else None,
		"current_reader_id": str(b.current_reader_id) if b.current_reader_id else None,
		"reading_status": _ev(b.reading_status),
		"condition": _ev(b.condition) if b.condition else None,
		"source": _ev(b.source) if b.source else None,
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


def _json_book(item: ExportBookItem) -> dict:  # type: ignore[type-arg]
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
		"reading_status": _ev(b.reading_status),
		"condition": _ev(b.condition) if b.condition else None,
		"source": _ev(b.source) if b.source else None,
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
	payload: dict = Depends(get_current_user_payload),  # type: ignore[type-arg]
	book_repo=Depends(get_owned_book_repository),
	record_repo=Depends(get_bibliographic_record_repository),
	room_repo=Depends(get_room_repository),
	bookcase_repo=Depends(get_bookcase_repository),
	section_repo=Depends(get_section_repository),
	shelf_repo=Depends(get_shelf_repository),
	book_read_repo=Depends(get_book_read_repository),
	book_loan_repo=Depends(get_book_loan_repository),
):  # type: ignore[no-untyped-def]
	items = await _build_use_case(
		book_repo, record_repo, room_repo, bookcase_repo,
		section_repo, shelf_repo, book_read_repo, book_loan_repo,
	).execute(UUID(payload["family_id"]), limit, offset)

	output = StringIO()
	writer = csv.DictWriter(output, fieldnames=_CSV_FIELDS)
	writer.writeheader()
	for item in items:
		writer.writerow(_csv_row(item))

	return StreamingResponse(
		iter([output.getvalue()]),
		media_type="text/csv",
		headers={"Content-Disposition": "attachment; filename=books.csv"},
	)


@router.get("/books.json", summary="Export books as JSON")
async def export_books_json(
	limit: int = Query(default=1000, ge=1, le=10000),
	offset: int = Query(default=0, ge=0),
	payload: dict = Depends(get_current_user_payload),  # type: ignore[type-arg]
	book_repo=Depends(get_owned_book_repository),
	record_repo=Depends(get_bibliographic_record_repository),
	room_repo=Depends(get_room_repository),
	bookcase_repo=Depends(get_bookcase_repository),
	section_repo=Depends(get_section_repository),
	shelf_repo=Depends(get_shelf_repository),
	book_read_repo=Depends(get_book_read_repository),
	book_loan_repo=Depends(get_book_loan_repository),
):  # type: ignore[no-untyped-def]
	items = await _build_use_case(
		book_repo, record_repo, room_repo, bookcase_repo,
		section_repo, shelf_repo, book_read_repo, book_loan_repo,
	).execute(UUID(payload["family_id"]), limit, offset)

	return {
		"exported_at": datetime.now(timezone.utc).isoformat(),
		"total": len(items),
		"books": [_json_book(item) for item in items],
	}
