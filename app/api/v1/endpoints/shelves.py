from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_bookcase_repository, get_current_user_payload, get_section_repository, get_shelf_repository, require_role
from app.application.use_cases import (
    CreateShelfInput,
    CreateShelfUseCase,
    DeleteShelfUseCase,
    GetShelfUseCase,
    ListShelvesUseCase,
    UpdateShelfInput,
    UpdateShelfUseCase,
)
from app.domain.repositories import BookcaseRepository, SectionRepository, ShelfRepository
from app.infrastructure.database.session import get_db

router = APIRouter()


class ShelfCreate(BaseModel):
    section_id: UUID
    shelf_index: int
    notes: str | None = None


class ShelfUpdate(BaseModel):
    section_id: UUID | None = None
    shelf_index: int | None = None
    notes: str | None = None


class ShelfResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    section_id: UUID
    shelf_index: int
    notes: str | None = None


@router.get("/", response_model=list[ShelfResponse])
async def list_shelves(
    section_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    payload: dict = Depends(get_current_user_payload),
    shelf_repo: ShelfRepository = Depends(get_shelf_repository),
    section_repo: SectionRepository = Depends(get_section_repository),
    bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
):
    try:
        return await ListShelvesUseCase(shelf_repo, section_repo, bookcase_repo).execute(UUID(payload["family_id"]), section_id, limit, offset)
    except LookupError:
        raise HTTPException(status_code=404, detail="Section not found")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.post("/", response_model=ShelfResponse, status_code=status.HTTP_201_CREATED)
async def create_shelf(
    request: ShelfCreate,
    payload: dict = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
    shelf_repo: ShelfRepository = Depends(get_shelf_repository),
    section_repo: SectionRepository = Depends(get_section_repository),
    bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
):
    try:
        created = await CreateShelfUseCase(shelf_repo, section_repo, bookcase_repo).execute(
            CreateShelfInput(family_id=UUID(payload["family_id"]), **request.model_dump())
        )
        await db.commit()
        return created
    except LookupError:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Section not found")
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(exc))


@router.get("/{shelf_id}", response_model=ShelfResponse)
async def get_shelf(
    shelf_id: UUID,
    payload: dict = Depends(get_current_user_payload),
    shelf_repo: ShelfRepository = Depends(get_shelf_repository),
    section_repo: SectionRepository = Depends(get_section_repository),
    bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
):
    try:
        return await GetShelfUseCase(shelf_repo, section_repo, bookcase_repo).execute(shelf_id, UUID(payload["family_id"]))
    except LookupError:
        raise HTTPException(status_code=404, detail="Shelf not found")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.patch("/{shelf_id}", response_model=ShelfResponse)
async def update_shelf(
    shelf_id: UUID,
    request: ShelfUpdate,
    payload: dict = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
    shelf_repo: ShelfRepository = Depends(get_shelf_repository),
    section_repo: SectionRepository = Depends(get_section_repository),
    bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
):
    try:
        updated = await UpdateShelfUseCase(shelf_repo, section_repo, bookcase_repo).execute(
            UpdateShelfInput(shelf_id=shelf_id, family_id=UUID(payload["family_id"]), **request.model_dump(exclude_unset=True))
        )
        await db.commit()
        return updated
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(exc))


@router.delete("/{shelf_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shelf(
    shelf_id: UUID,
    payload: dict = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
    shelf_repo: ShelfRepository = Depends(get_shelf_repository),
    section_repo: SectionRepository = Depends(get_section_repository),
    bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
):
    try:
        await DeleteShelfUseCase(shelf_repo, section_repo, bookcase_repo).execute(shelf_id, UUID(payload["family_id"]))
        await db.commit()
    except LookupError:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Shelf not found")
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(exc))
