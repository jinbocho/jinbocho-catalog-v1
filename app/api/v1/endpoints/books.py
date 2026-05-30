from datetime import date
from decimal import Decimal
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_bibliographic_record_repository,
    get_book_history_repository,
    get_bookcase_repository,
    get_current_user_payload,
    get_http_client,
    get_isbn_lookup_cache_repository,
    get_owned_book_repository,
    get_room_repository,
    get_section_repository,
    get_shelf_repository,
    require_role,
)
from app.application.use_cases import (
    AddBookInput,
    AddBookUseCase,
    DeleteBookInput,
    DeleteBookUseCase,
    UpdateBookPositionInput,
    UpdateBookPositionUseCase,
    UpdateReadingStatusInput,
    UpdateReadingStatusUseCase,
)
from app.domain.repositories import (
    BibliographicRecordRepository,
    BookHistoryRepository,
    BookcaseRepository,
    IsbnLookupCacheRepository,
    OwnedBookRepository,
    RoomRepository,
    SectionRepository,
    ShelfRepository,
)
from app.infrastructure.database.session import get_db
from app.utils import utcnow

router = APIRouter()


class OwnedBookCreate(BaseModel):
    isbn: str | None = None
    title: str | None = Field(default=None, max_length=500)
    main_author: str | None = None
    other_authors: list[str] = []
    publisher: str | None = None
    publication_year: int | None = None
    language: str | None = None
    genre: str | None = None
    cover_url: str | None = None
    record_notes: str | None = None
    bibliographic_record_id: UUID | None = None
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
    reading_status: str = "to_read"
    tags: list[str] = []
    notes: str | None = None
    is_intentional_duplicate: bool = False
    duplicate_notes: str | None = None


class OwnedBookUpdate(BaseModel):
    condition: str | None = None
    purchase_date: date | None = None
    purchase_price: float | None = None
    source: str | None = None
    reading_status: str | None = None
    tags: list[str] | None = None
    notes: str | None = None
    is_intentional_duplicate: bool | None = None
    duplicate_notes: str | None = None
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
    purchase_date: str | None = None
    purchase_price: float | None = None
    source: str | None = None
    reading_status: str
    tags: list[str] | None = None
    notes: str | None = None
    is_intentional_duplicate: bool
    duplicate_notes: str | None = None


class OwnedBookDetailResponse(OwnedBookResponse):
    title: str | None = None
    main_author: str | None = None
    isbn: str | None = None
    cover_url: str | None = None


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
    shelf_id: UUID | None = None,
    reading_status: str | None = None,
    tag: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    payload: dict = Depends(get_current_user_payload),
    book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
):
    family_id = UUID(payload["family_id"])
    return await book_repo.find_all_by_family(
        family_id,
        shelf_id=shelf_id,
        reading_status=reading_status,
        tag=tag,
        limit=limit,
        offset=offset,
    )


@router.post("/", response_model=OwnedBookResponse, status_code=status.HTTP_201_CREATED)
async def add_book(
    request: OwnedBookCreate,
    payload: dict = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
    book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
    history_repo: BookHistoryRepository = Depends(get_book_history_repository),
    cache_repo: IsbnLookupCacheRepository = Depends(get_isbn_lookup_cache_repository),
    room_repo: RoomRepository = Depends(get_room_repository),
    bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
    section_repo: SectionRepository = Depends(get_section_repository),
    shelf_repo: ShelfRepository = Depends(get_shelf_repository),
):
    family_id = UUID(payload["family_id"])
    user_id = UUID(payload["sub"])
    if not request.isbn and not request.title and not request.bibliographic_record_id:
        raise HTTPException(status_code=422, detail="Provide at least one of: isbn, title, or bibliographic_record_id")

    use_case = AddBookUseCase(
        record_repo=record_repo,
        book_repo=book_repo,
        history_repo=history_repo,
        cache_repo=cache_repo,
        room_repo=room_repo,
        bookcase_repo=bookcase_repo,
        section_repo=section_repo,
        shelf_repo=shelf_repo,
        http_client=http_client,
    )
    try:
        created = await use_case.execute(
            AddBookInput(
                family_id=family_id,
                changed_by=user_id,
                bibliographic_record_id=request.bibliographic_record_id,
                title=request.title,
                main_author=request.main_author,
                other_authors=request.other_authors,
                isbn=request.isbn.replace("-", "").strip() if request.isbn else None,
                publisher=request.publisher,
                publication_year=request.publication_year,
                language=request.language,
                genre=request.genre,
                cover_url=request.cover_url,
                record_notes=request.record_notes,
                notes=request.notes,
                room_id=request.room_id,
                bookcase_id=request.bookcase_id,
                section_id=request.section_id,
                shelf_id=request.shelf_id,
                shelf_position=request.shelf_position,
                position_description=request.position_description,
                condition=request.condition,
                purchase_date=request.purchase_date,
                purchase_price=Decimal(str(request.purchase_price)) if request.purchase_price is not None else None,
                source=request.source,
                reading_status=request.reading_status,
                tags=request.tags,
                is_intentional_duplicate=request.is_intentional_duplicate,
                duplicate_notes=request.duplicate_notes,
            )
        )
        await db.commit()
        return created
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate entry or constraint violation")
    except (LookupError, ValueError) as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(exc))


@router.get("/{book_id}", response_model=OwnedBookDetailResponse)
async def get_book(
    book_id: UUID,
    payload: dict = Depends(get_current_user_payload),
    book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
    record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
):
    family_id = UUID(payload["family_id"])
    book = await book_repo.find_by_id(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.family_id != family_id:
        raise HTTPException(status_code=403, detail="Access denied")
    record = await record_repo.find_by_id(book.bibliographic_record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Bibliographic record not found")
    return OwnedBookDetailResponse(
        **OwnedBookResponse.model_validate(book).model_dump(),
        title=record.title,
        main_author=record.main_author,
        isbn=record.isbn,
        cover_url=record.cover_url,
    )


@router.patch("/{book_id}", response_model=OwnedBookResponse)
async def update_book(
    book_id: UUID,
    request: OwnedBookUpdate,
    payload: dict = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
    book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
    history_repo: BookHistoryRepository = Depends(get_book_history_repository),
    room_repo: RoomRepository = Depends(get_room_repository),
    bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
    section_repo: SectionRepository = Depends(get_section_repository),
    shelf_repo: ShelfRepository = Depends(get_shelf_repository),
):
    family_id = UUID(payload["family_id"])
    user_id = UUID(payload["sub"])
    update_data = request.model_dump(exclude_unset=True)
    current_book = await book_repo.find_by_id(book_id)
    if current_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if current_book.family_id != family_id:
        raise HTTPException(status_code=403, detail="Access denied")

    position_fields = {"room_id", "bookcase_id", "section_id", "shelf_id", "shelf_position", "position_description"}
    has_position_update = bool(position_fields & set(update_data))
    has_status_update = "reading_status" in update_data

    try:
        if has_position_update:
            position_use_case = UpdateBookPositionUseCase(
                book_repo=book_repo,
                history_repo=history_repo,
                room_repo=room_repo,
                bookcase_repo=bookcase_repo,
                section_repo=section_repo,
                shelf_repo=shelf_repo,
            )
            await position_use_case.execute(
                UpdateBookPositionInput(
                    book_id=book_id,
                    family_id=family_id,
                    changed_by=user_id,
                    room_id=update_data["room_id"] if "room_id" in update_data else current_book.room_id,
                    bookcase_id=update_data["bookcase_id"] if "bookcase_id" in update_data else current_book.bookcase_id,
                    section_id=update_data["section_id"] if "section_id" in update_data else current_book.section_id,
                    shelf_id=update_data["shelf_id"] if "shelf_id" in update_data else current_book.shelf_id,
                    shelf_position=update_data["shelf_position"] if "shelf_position" in update_data else current_book.shelf_position,
                    position_description=(
                        update_data["position_description"]
                        if "position_description" in update_data
                        else current_book.position_description
                    ),
                )
            )

        if has_status_update:
            status_use_case = UpdateReadingStatusUseCase(book_repo=book_repo, history_repo=history_repo)
            await status_use_case.execute(
                UpdateReadingStatusInput(
                    book_id=book_id,
                    family_id=family_id,
                    changed_by=user_id,
                    reading_status=update_data["reading_status"],
                )
            )

        remaining = {k: v for k, v in update_data.items() if k not in position_fields and k != "reading_status"}
        if remaining:
            current_book = await book_repo.find_by_id(book_id)
            if current_book is None:
                raise HTTPException(status_code=404, detail="Book not found")
            for field_name, value in remaining.items():
                if field_name == "purchase_price" and value is not None:
                    setattr(current_book, field_name, Decimal(str(value)))
                else:
                    setattr(current_book, field_name, value)
            current_book.updated_at = utcnow()
            await book_repo.save(current_book)

        await db.commit()
        updated = await book_repo.find_by_id(book_id)
        if updated is None:
            raise HTTPException(status_code=404, detail="Book not found")
        return updated
    except LookupError:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Book not found")
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate entry or constraint violation")


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: UUID,
    payload: dict = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
    book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
    history_repo: BookHistoryRepository = Depends(get_book_history_repository),
):
    use_case = DeleteBookUseCase(book_repo=book_repo, history_repo=history_repo)
    try:
        await use_case.execute(
            DeleteBookInput(book_id=book_id, family_id=UUID(payload["family_id"]), changed_by=UUID(payload["sub"]))
        )
        await db.commit()
    except LookupError:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Book not found")
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(exc))


@router.get("/{book_id}/history", response_model=list[BookHistoryResponse])
async def get_book_history(
    book_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    payload: dict = Depends(get_current_user_payload),
    book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
    history_repo: BookHistoryRepository = Depends(get_book_history_repository),
):
    book = await book_repo.find_by_id(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.family_id != UUID(payload["family_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    return await history_repo.find_by_book(book_id, limit=limit, offset=offset)
