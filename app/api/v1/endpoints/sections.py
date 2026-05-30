from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_bookcase_repository, get_current_user_payload, get_section_repository, require_role
from app.application.use_cases import (
    CreateSectionInput,
    CreateSectionUseCase,
    DeleteSectionUseCase,
    GetSectionUseCase,
    ListSectionsUseCase,
    UpdateSectionInput,
    UpdateSectionUseCase,
)
from app.domain.repositories import BookcaseRepository, SectionRepository
from app.infrastructure.database.session import get_db

router = APIRouter()


class SectionCreate(BaseModel):
    bookcase_id: UUID
    section_index: int
    label: str | None = None


class SectionUpdate(BaseModel):
    bookcase_id: UUID | None = None
    section_index: int | None = None
    label: str | None = None


class SectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bookcase_id: UUID
    section_index: int
    label: str | None = None


@router.get("/", response_model=list[SectionResponse])
async def list_sections(
    bookcase_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    payload: dict = Depends(get_current_user_payload),
    section_repo: SectionRepository = Depends(get_section_repository),
    bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
):
    try:
        return await ListSectionsUseCase(section_repo, bookcase_repo).execute(UUID(payload["family_id"]), bookcase_id, limit, offset)
    except LookupError:
        raise HTTPException(status_code=404, detail="Bookcase not found")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.post("/", response_model=SectionResponse, status_code=status.HTTP_201_CREATED)
async def create_section(
    request: SectionCreate,
    payload: dict = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
    section_repo: SectionRepository = Depends(get_section_repository),
    bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
):
    try:
        created = await CreateSectionUseCase(section_repo, bookcase_repo).execute(
            CreateSectionInput(family_id=UUID(payload["family_id"]), **request.model_dump())
        )
        await db.commit()
        return created
    except LookupError:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Bookcase not found")
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(exc))


@router.get("/{section_id}", response_model=SectionResponse)
async def get_section(
    section_id: UUID,
    payload: dict = Depends(get_current_user_payload),
    section_repo: SectionRepository = Depends(get_section_repository),
    bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
):
    try:
        return await GetSectionUseCase(section_repo, bookcase_repo).execute(section_id, UUID(payload["family_id"]))
    except LookupError:
        raise HTTPException(status_code=404, detail="Section not found")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.patch("/{section_id}", response_model=SectionResponse)
async def update_section(
    section_id: UUID,
    request: SectionUpdate,
    payload: dict = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
    section_repo: SectionRepository = Depends(get_section_repository),
    bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
):
    try:
        updated = await UpdateSectionUseCase(section_repo, bookcase_repo).execute(
            UpdateSectionInput(section_id=section_id, family_id=UUID(payload["family_id"]), **request.model_dump(exclude_unset=True))
        )
        await db.commit()
        return updated
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(exc))


@router.delete("/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(
    section_id: UUID,
    payload: dict = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
    section_repo: SectionRepository = Depends(get_section_repository),
    bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
):
    try:
        await DeleteSectionUseCase(section_repo, bookcase_repo).execute(section_id, UUID(payload["family_id"]))
        await db.commit()
    except LookupError:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Section not found")
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(exc))
