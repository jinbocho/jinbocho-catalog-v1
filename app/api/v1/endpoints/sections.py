from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_bookcase_repository, get_current_user_payload, get_section_repository, require_role
from app.api.v1.schemas.section_schemas import SectionCreate, SectionResponse, SectionUpdate
from app.application.use_cases import (
	CreateSectionInput,
	CreateSectionUseCase,
	DeleteSectionUseCase,
	GetSectionUseCase,
	ListSectionsUseCase,
	UpdateSectionInput,
	UpdateSectionUseCase,
)
from app.infrastructure.database.session import get_db

router = APIRouter(tags=["sections"])


@router.get("/", response_model=list[SectionResponse], summary="List sections")
async def list_sections(
	bookcase_id: UUID | None = None,
	limit: int = Query(default=50, ge=1, le=200),
	offset: int = Query(default=0, ge=0),
	payload: dict = Depends(get_current_user_payload),
	section_repo = Depends(get_section_repository),
	bookcase_repo = Depends(get_bookcase_repository),
):
	return await ListSectionsUseCase(section_repo, bookcase_repo).execute(UUID(payload["family_id"]), bookcase_id, limit, offset)


@router.post("/", response_model=SectionResponse, status_code=status.HTTP_201_CREATED, summary="Create section")
async def create_section(
	request: SectionCreate,
	payload: dict = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	section_repo = Depends(get_section_repository),
	bookcase_repo = Depends(get_bookcase_repository),
):
	created = await CreateSectionUseCase(section_repo, bookcase_repo).execute(
		CreateSectionInput(family_id=UUID(payload["family_id"]), **request.model_dump())
	)
	await db.commit()
	return created


@router.get("/{section_id}", response_model=SectionResponse, summary="Get section")
async def get_section(
	section_id: UUID,
	payload: dict = Depends(get_current_user_payload),
	section_repo = Depends(get_section_repository),
	bookcase_repo = Depends(get_bookcase_repository),
):
	return await GetSectionUseCase(section_repo, bookcase_repo).execute(section_id, UUID(payload["family_id"]))


@router.patch("/{section_id}", response_model=SectionResponse, summary="Update section")
async def update_section(
	section_id: UUID,
	request: SectionUpdate,
	payload: dict = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	section_repo = Depends(get_section_repository),
	bookcase_repo = Depends(get_bookcase_repository),
):
	updated = await UpdateSectionUseCase(section_repo, bookcase_repo).execute(
		UpdateSectionInput(section_id=section_id, family_id=UUID(payload["family_id"]), **request.model_dump(exclude_unset=True))
	)
	await db.commit()
	return updated


@router.delete("/{section_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete section")
async def delete_section(
	section_id: UUID,
	payload: dict = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	section_repo = Depends(get_section_repository),
	bookcase_repo = Depends(get_bookcase_repository),
):
	await DeleteSectionUseCase(section_repo, bookcase_repo).execute(section_id, UUID(payload["family_id"]))
	await db.commit()
