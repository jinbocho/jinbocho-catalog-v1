from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases import AddBookWithPosition, AddBookWithPositionInput, MoveBook, MoveBookInput
from app.infrastructure.database.session import get_db
from app.infrastructure.models import BookHistoryModel, OwnedBookModel

router = APIRouter()


class OwnedBookCreate(BaseModel):
    family_id: UUID
    bibliographic_record_id: UUID | None = None
    title: str = Field(min_length=1, max_length=500)
    main_author: str | None = None
    other_authors: list[str] = []
    isbn: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    language: str | None = None
    genre: str | None = None
    cover_url: str | None = None
    notes: str | None = None
    room_id: UUID | None = None
    bookcase_id: UUID | None = None
    section_id: UUID | None = None
    shelf_id: UUID | None = None
    shelf_position: int | None = None
    position_description: str | None = None
    reading_status: str = "to_read"
    tags: list[str] = []
    changed_by: UUID | None = None


class OwnedBookUpdate(BaseModel):
    room_id: UUID | None = None
    bookcase_id: UUID | None = None
    section_id: UUID | None = None
    shelf_id: UUID | None = None
    shelf_position: int | None = None
    position_description: str | None = None
    condition: str | None = None
    purchase_date: date | None = None
    purchase_price: float | None = None
    source: str | None = None
    reading_status: str | None = None
    tags: list[str] | None = None
    notes: str | None = None
    is_intentional_duplicate: bool | None = None
    duplicate_notes: str | None = None


class BookPositionUpdate(BaseModel):
    changed_by: UUID
    room_id: UUID | None = None
    bookcase_id: UUID | None = None
    section_id: UUID | None = None
    shelf_id: UUID | None = None
    shelf_position: int | None = None
    position_description: str | None = None


class OwnedBookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    family_id: UUID
    bibliographic_record_id: UUID
    room_id: UUID | None = None
    bookcase_id: UUID | None = None
    section_id: UUID | None = None
    shelf_id: UUID | None = None
    shelf_position: int | None = None
    position_description: str | None = None
    condition: str | None = None
    purchase_price: float | None = None
    source: str | None = None
    reading_status: str
    tags: list[str] | None = None
    notes: str | None = None
    is_intentional_duplicate: bool
    duplicate_notes: str | None = None


class BookHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owned_book_id: UUID
    event_type: str
    changed_by: UUID
    old_data: dict | None = None
    new_data: dict | None = None


@router.get("/", response_model=list[OwnedBookResponse])
async def list_books(
    family_id: UUID,
    reading_status: str | None = None,
    shelf_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(OwnedBookModel).where(OwnedBookModel.family_id == family_id)
    if reading_status is not None:
        query = query.where(OwnedBookModel.reading_status == reading_status)
    if shelf_id is not None:
        query = query.where(OwnedBookModel.shelf_id == shelf_id)
    result = await db.execute(query.order_by(OwnedBookModel.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=OwnedBookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(request: OwnedBookCreate, db: AsyncSession = Depends(get_db)):
    use_case = AddBookWithPosition()
    book = await use_case.execute(
        db,
        AddBookWithPositionInput(
            family_id=request.family_id,
            title=request.title,
            main_author=request.main_author,
            other_authors=request.other_authors,
            isbn=request.isbn,
            publisher=request.publisher,
            publication_year=request.publication_year,
            language=request.language,
            genre=request.genre,
            cover_url=request.cover_url,
            notes=request.notes,
            bibliographic_record_id=request.bibliographic_record_id,
            room_id=request.room_id,
            bookcase_id=request.bookcase_id,
            section_id=request.section_id,
            shelf_id=request.shelf_id,
            shelf_position=request.shelf_position,
            position_description=request.position_description,
            reading_status=request.reading_status,
            tags=request.tags,
            changed_by=request.changed_by,
        ),
    )
    await db.commit()
    await db.refresh(book)
    return book


@router.get("/{book_id}", response_model=OwnedBookResponse)
async def get_book(book_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OwnedBookModel).where(OwnedBookModel.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


@router.patch("/{book_id}", response_model=OwnedBookResponse)
async def update_book(book_id: UUID, request: OwnedBookUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OwnedBookModel).where(OwnedBookModel.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    old_status = book.reading_status
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(book, field, value)
    book.updated_at = datetime.utcnow()

    if request.reading_status is not None and request.reading_status != old_status:
        db.add(
            BookHistoryModel(
                owned_book_id=book.id,
                event_type="reading_status_changed",
                changed_by=book.family_id,
                old_data={"reading_status": old_status},
                new_data={"reading_status": request.reading_status},
            )
        )
    await db.commit()
    await db.refresh(book)
    return book


@router.patch("/{book_id}/position", response_model=OwnedBookResponse)
async def move_book(book_id: UUID, request: BookPositionUpdate, db: AsyncSession = Depends(get_db)):
    use_case = MoveBook()
    book = await use_case.execute(
        db,
        MoveBookInput(
            owned_book_id=book_id,
            changed_by=request.changed_by,
            room_id=request.room_id,
            bookcase_id=request.bookcase_id,
            section_id=request.section_id,
            shelf_id=request.shelf_id,
            shelf_position=request.shelf_position,
            position_description=request.position_description,
        ),
    )
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    await db.commit()
    await db.refresh(book)
    return book


@router.get("/{book_id}/history", response_model=list[BookHistoryResponse])
async def get_book_history(book_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BookHistoryModel).where(BookHistoryModel.owned_book_id == book_id).order_by(BookHistoryModel.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OwnedBookModel).where(OwnedBookModel.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    db.add(
        BookHistoryModel(
            owned_book_id=book.id,
            event_type="deleted",
            changed_by=book.family_id,
            old_data={"reading_status": book.reading_status, "shelf_id": str(book.shelf_id) if book.shelf_id else None},
        )
    )
    await db.delete(book)
    await db.commit()
