import csv
from io import StringIO
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_bibliographic_record_repository, get_current_user_payload, get_owned_book_repository
from app.application.use_cases import ExportBooksUseCase

router = APIRouter(tags=["export"])


@router.get("/books.csv", summary="Export books as CSV")
async def export_books_csv(
	limit: int = Query(default=1000, ge=1, le=10000),
	offset: int = Query(default=0, ge=0),
	payload: dict = Depends(get_current_user_payload),
	book_repo = Depends(get_owned_book_repository),
	record_repo = Depends(get_bibliographic_record_repository),
):
	items = await ExportBooksUseCase(book_repo, record_repo).execute(UUID(payload["family_id"]), limit, offset)

	# Create CSV
	output = StringIO()
	writer = csv.DictWriter(output, fieldnames=[
		"book_id", "title", "main_author", "isbn", "publisher", "publication_year",
		"reading_status", "room_id", "bookcase_id", "section_id", "shelf_id", "shelf_position"
	])
	writer.writeheader()

	for item in items:
		writer.writerow({
			"book_id": str(item.book.id),
			"title": item.record.title if item.record else None,
			"main_author": item.record.main_author if item.record else None,
			"isbn": item.record.isbn if item.record else None,
			"publisher": item.record.publisher if item.record else None,
			"publication_year": item.record.publication_year if item.record else None,
			"reading_status": item.book.reading_status,
			"room_id": item.book.room_id,
			"bookcase_id": item.book.bookcase_id,
			"section_id": item.book.section_id,
			"shelf_id": item.book.shelf_id,
			"shelf_position": item.book.shelf_position,
		})

	return StreamingResponse(
		iter([output.getvalue()]),
		media_type="text/csv",
		headers={"Content-Disposition": "attachment; filename=books.csv"}
	)


@router.get("/books.json", summary="Export books as JSON")
async def export_books_json(
	limit: int = Query(default=1000, ge=1, le=10000),
	offset: int = Query(default=0, ge=0),
	payload: dict = Depends(get_current_user_payload),
	book_repo = Depends(get_owned_book_repository),
	record_repo = Depends(get_bibliographic_record_repository),
):
	items = await ExportBooksUseCase(book_repo, record_repo).execute(UUID(payload["family_id"]), limit, offset)
	return {
		"books": [
			{
				"book_id": str(item.book.id),
				"title": item.record.title if item.record else None,
				"main_author": item.record.main_author if item.record else None,
				"isbn": item.record.isbn if item.record else None,
				"reading_status": item.book.reading_status,
			}
			for item in items
		]
	}
