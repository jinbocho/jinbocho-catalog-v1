import csv
from io import StringIO
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db
from app.infrastructure.models import BibliographicRecordModel, OwnedBookModel

router = APIRouter()


async def _fetch_books(family_id: UUID, db: AsyncSession):
    result = await db.execute(
        select(OwnedBookModel, BibliographicRecordModel)
        .join(
            BibliographicRecordModel,
            OwnedBookModel.bibliographic_record_id == BibliographicRecordModel.id,
        )
        .where(OwnedBookModel.family_id == family_id)
        .order_by(OwnedBookModel.created_at.desc())
    )
    return result.all()


@router.get("/csv")
async def export_csv(family_id: UUID, db: AsyncSession = Depends(get_db)):
    rows = await _fetch_books(family_id, db)
    buffer = StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "owned_book_id",
            "title",
            "main_author",
            "isbn",
            "reading_status",
            "room_id",
            "bookcase_id",
            "section_id",
            "shelf_id",
            "shelf_position",
            "position_description",
            "tags",
            "notes",
        ],
    )
    writer.writeheader()
    for owned_book, record in rows:
        writer.writerow(
            {
                "owned_book_id": str(owned_book.id),
                "title": record.title,
                "main_author": record.main_author,
                "isbn": record.isbn,
                "reading_status": owned_book.reading_status,
                "room_id": owned_book.room_id,
                "bookcase_id": owned_book.bookcase_id,
                "section_id": owned_book.section_id,
                "shelf_id": owned_book.shelf_id,
                "shelf_position": owned_book.shelf_position,
                "position_description": owned_book.position_description,
                "tags": ",".join(owned_book.tags or []),
                "notes": owned_book.notes,
            }
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="jinbocho-{family_id}.csv"'},
    )


@router.get("/json")
async def export_json(family_id: UUID, db: AsyncSession = Depends(get_db)):
    rows = await _fetch_books(family_id, db)
    payload = [
        {
            "owned_book": jsonable_encoder(owned_book),
            "bibliographic_record": jsonable_encoder(record),
        }
        for owned_book, record in rows
    ]
    return payload
