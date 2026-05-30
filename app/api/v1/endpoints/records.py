from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_bibliographic_record_repository, get_current_user_payload, get_owned_book_repository, require_role
from app.application.use_cases import (
    CreateBibliographicRecordInput,
    CreateBibliographicRecordUseCase,
    DeleteBibliographicRecordUseCase,
    ListBibliographicRecordsUseCase,
    UpdateBibliographicRecordInput,
    UpdateBibliographicRecordUseCase,
)
from app.domain.repositories import BibliographicRecordRepository, OwnedBookRepository
from app.infrastructure.database.session import get_db

router = APIRouter()


class BibliographicRecordCreate(BaseModel):
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


class BibliographicRecordUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    main_author: str | None = None
    other_authors: list[str] | None = None
    isbn: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    language: str | None = None
    genre: str | None = None
    cover_url: str | None = None
    notes: str | None = None


class BibliographicRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    family_id: UUID
    title: str
    main_author: str | None = None
    other_authors: list[str] | None = None
    isbn: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    language: str | None = None
    genre: str | None = None
    cover_url: str | None = None
    notes: str | None = None


@router.get("/", response_model=list[BibliographicRecordResponse])
async def list_records(
    q: str | None = Query(default=None, description="Full-text search across title, author, isbn"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    payload: dict = Depends(get_current_user_payload),
    record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
):
    return await ListBibliographicRecordsUseCase(record_repo).execute(UUID(payload["family_id"]), q, limit, offset)


@router.post("/", response_model=BibliographicRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_record(
    request: BibliographicRecordCreate,
    payload: dict = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
    record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
):
    try:
        created = await CreateBibliographicRecordUseCase(record_repo).execute(
            CreateBibliographicRecordInput(
                family_id=UUID(payload["family_id"]),
                title=request.title,
                main_author=request.main_author,
                other_authors=request.other_authors,
                isbn=request.isbn.replace("-", "").strip() if request.isbn else None,
                publisher=request.publisher,
                publication_year=request.publication_year,
                language=request.language,
                genre=request.genre,
                cover_url=request.cover_url,
                notes=request.notes,
            )
        )
        await db.commit()
        return created
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate entry or constraint violation")


@router.get("/{record_id}", response_model=BibliographicRecordResponse)
async def get_record(
    record_id: UUID,
    payload: dict = Depends(get_current_user_payload),
    record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
):
    record = await record_repo.find_by_id(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Bibliographic record not found")
    if record.family_id != UUID(payload["family_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    return record


@router.patch("/{record_id}", response_model=BibliographicRecordResponse)
async def update_record(
    record_id: UUID,
    request: BibliographicRecordUpdate,
    payload: dict = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
    record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
):
    update_data = request.model_dump(exclude_unset=True)
    if "isbn" in update_data and update_data["isbn"]:
        update_data["isbn"] = update_data["isbn"].replace("-", "").strip()
    try:
        updated = await UpdateBibliographicRecordUseCase(record_repo).execute(
            UpdateBibliographicRecordInput(record_id=record_id, family_id=UUID(payload["family_id"]), **update_data)
        )
        await db.commit()
        return updated
    except LookupError:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Bibliographic record not found")
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(exc))
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate entry or constraint violation")


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(
    record_id: UUID,
    payload: dict = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
    record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
    book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
):
    try:
        await DeleteBibliographicRecordUseCase(record_repo, book_repo).execute(record_id, UUID(payload["family_id"]))
        await db.commit()
    except LookupError:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Bibliographic record not found")
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
