import csv
from io import StringIO
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.dependencies import get_bibliographic_record_repository, get_current_user_payload, get_owned_book_repository
from app.application.use_cases import ExportBookItem, ExportBooksUseCase
from app.domain.repositories import BibliographicRecordRepository, OwnedBookRepository
from app.limiter import limiter

router = APIRouter()


class BookExportResponse(BaseModel):
    book_id: UUID
    bibliographic_record_id: UUID
    title: str | None = None
    main_author: str | None = None
    isbn: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    reading_status: str
    room_id: UUID | None = None
    bookcase_id: UUID | None = None
    section_id: UUID | None = None
    shelf_id: UUID | None = None
    shelf_position: int | None = None
    tags: list[str] | None = None
    notes: str | None = None


@router.get("/csv")
@limiter.limit("5/minute")
async def export_csv(
    request: Request,
    response: Response,
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    payload: dict = Depends(get_current_user_payload),
    book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
    record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
):
    items = await ExportBooksUseCase(book_repo, record_repo).execute(UUID(payload["family_id"]), limit, offset)
    _set_next_link(request, response, items, limit, offset)

    async def generate_csv():
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow([
            "book_id",
            "title",
            "main_author",
            "isbn",
            "publisher",
            "publication_year",
            "reading_status",
            "room_id",
            "bookcase_id",
            "section_id",
            "shelf_id",
            "shelf_position",
            "tags",
            "notes",
        ])
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        for item in items:
            record = item.record
            writer.writerow([
                item.book.id,
                record.title if record else None,
                record.main_author if record else None,
                record.isbn if record else None,
                record.publisher if record else None,
                record.publication_year if record else None,
                item.book.reading_status,
                item.book.room_id,
                item.book.bookcase_id,
                item.book.section_id,
                item.book.shelf_id,
                item.book.shelf_position,
                ";".join(item.book.tags or []),
                item.book.notes,
            ])
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=books.csv", **dict(response.headers)},
    )


@router.get("/json", response_model=list[BookExportResponse])
@limiter.limit("5/minute")
async def export_json(
    request: Request,
    response: Response,
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    payload: dict = Depends(get_current_user_payload),
    book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
    record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
):
    items = await ExportBooksUseCase(book_repo, record_repo).execute(UUID(payload["family_id"]), limit, offset)
    _set_next_link(request, response, items, limit, offset)
    return [_to_export_response(item) for item in items]


def _to_export_response(item: ExportBookItem) -> BookExportResponse:
    record = item.record
    return BookExportResponse(
        book_id=item.book.id,
        bibliographic_record_id=item.book.bibliographic_record_id,
        title=record.title if record else None,
        main_author=record.main_author if record else None,
        isbn=record.isbn if record else None,
        publisher=record.publisher if record else None,
        publication_year=record.publication_year if record else None,
        reading_status=item.book.reading_status,
        room_id=item.book.room_id,
        bookcase_id=item.book.bookcase_id,
        section_id=item.book.section_id,
        shelf_id=item.book.shelf_id,
        shelf_position=item.book.shelf_position,
        tags=item.book.tags,
        notes=item.book.notes,
    )


def _set_next_link(request: Request, response: Response, items: list[ExportBookItem], limit: int, offset: int) -> None:
    if len(items) == limit:
        next_url = str(request.url.include_query_params(limit=limit, offset=offset + limit))
        response.headers["Link"] = f'<{next_url}>; rel="next"'
