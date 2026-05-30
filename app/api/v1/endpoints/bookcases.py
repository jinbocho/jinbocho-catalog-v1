from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_bookcase_repository, get_current_user_payload, get_room_repository, require_role
from app.application.use_cases import (
    CreateBookcaseInput,
    CreateBookcaseUseCase,
    DeleteBookcaseUseCase,
    GetBookcaseUseCase,
    ListBookcasesUseCase,
    UpdateBookcaseInput,
    UpdateBookcaseUseCase,
)
from app.domain.repositories import BookcaseRepository, RoomRepository
from app.infrastructure.database.session import get_db

router = APIRouter()


class BookcaseCreate(BaseModel):
    room_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    type: str | None = None
    notes: str | None = None
    image_url: str | None = None


class BookcaseUpdate(BaseModel):
    room_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    type: str | None = None
    notes: str | None = None
    image_url: str | None = None


class BookcaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    family_id: UUID
    room_id: UUID
    name: str
    description: str | None = None
    type: str | None = None
    notes: str | None = None
    image_url: str | None = None


@router.get("/", response_model=list[BookcaseResponse])
async def list_bookcases(
    room_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    payload: dict = Depends(get_current_user_payload),
    bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
    room_repo: RoomRepository = Depends(get_room_repository),
):
    try:
        return await ListBookcasesUseCase(bookcase_repo, room_repo).execute(UUID(payload["family_id"]), room_id, limit, offset)
    except LookupError:
        raise HTTPException(status_code=404, detail="Room not found")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.post("/", response_model=BookcaseResponse, status_code=status.HTTP_201_CREATED)
async def create_bookcase(
    request: BookcaseCreate,
    payload: dict = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
    bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
    room_repo: RoomRepository = Depends(get_room_repository),
):
    try:
        created = await CreateBookcaseUseCase(bookcase_repo, room_repo).execute(
            CreateBookcaseInput(family_id=UUID(payload["family_id"]), **request.model_dump())
        )
        await db.commit()
        return created
    except LookupError:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Room not found")
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(exc))


@router.get("/{bookcase_id}", response_model=BookcaseResponse)
async def get_bookcase(
    bookcase_id: UUID,
    payload: dict = Depends(get_current_user_payload),
    bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
):
    try:
        return await GetBookcaseUseCase(bookcase_repo).execute(bookcase_id, UUID(payload["family_id"]))
    except LookupError:
        raise HTTPException(status_code=404, detail="Bookcase not found")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.patch("/{bookcase_id}", response_model=BookcaseResponse)
async def update_bookcase(
    bookcase_id: UUID,
    request: BookcaseUpdate,
    payload: dict = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
    bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
    room_repo: RoomRepository = Depends(get_room_repository),
):
    try:
        updated = await UpdateBookcaseUseCase(bookcase_repo, room_repo).execute(
            UpdateBookcaseInput(bookcase_id=bookcase_id, family_id=UUID(payload["family_id"]), **request.model_dump(exclude_unset=True))
        )
        await db.commit()
        return updated
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(exc))


@router.delete("/{bookcase_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookcase(
    bookcase_id: UUID,
    payload: dict = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
    bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
):
    try:
        await DeleteBookcaseUseCase(bookcase_repo).execute(bookcase_id, UUID(payload["family_id"]))
        await db.commit()
    except LookupError:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Bookcase not found")
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(exc))
