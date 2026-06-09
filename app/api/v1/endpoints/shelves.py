from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_bookcase_repository, get_current_user_payload, get_section_repository, get_shelf_repository, require_role
from app.api.v1.schemas.shelf_schemas import ShelfCreate, ShelfResponse, ShelfUpdate
from app.application.use_cases import (
	CreateShelfInput,
	CreateShelfUseCase,
	DeleteShelfUseCase,
	GetShelfUseCase,
	ListShelvesUseCase,
	UpdateShelfInput,
	UpdateShelfUseCase,
)
from app.infrastructure.database.session import get_db

router = APIRouter(tags=["shelves"])


@router.get("/", response_model=list[ShelfResponse], summary="List shelves")
async def list_shelves(
	section_id: UUID | None = None,
	limit: int = Query(default=50, ge=1, le=200),
	offset: int = Query(default=0, ge=0),
	payload: dict = Depends(get_current_user_payload),
	shelf_repo = Depends(get_shelf_repository),
	section_repo = Depends(get_section_repository),
	bookcase_repo = Depends(get_bookcase_repository),
):
	return await ListShelvesUseCase(shelf_repo, section_repo, bookcase_repo).execute(UUID(payload["family_id"]), section_id, limit, offset)


@router.post("/", response_model=ShelfResponse, status_code=status.HTTP_201_CREATED, summary="Create shelf")
async def create_shelf(
	request: ShelfCreate,
	payload: dict = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	shelf_repo = Depends(get_shelf_repository),
	section_repo = Depends(get_section_repository),
	bookcase_repo = Depends(get_bookcase_repository),
):
	created = await CreateShelfUseCase(shelf_repo, section_repo).execute(
		CreateShelfInput(family_id=UUID(payload["family_id"]), **request.model_dump())
	)
	await db.commit()
	return created


@router.get("/{shelf_id}", response_model=ShelfResponse, summary="Get shelf")
async def get_shelf(
	shelf_id: UUID,
	payload: dict = Depends(get_current_user_payload),
	shelf_repo = Depends(get_shelf_repository),
	section_repo = Depends(get_section_repository),
	bookcase_repo = Depends(get_bookcase_repository),
):
	return await GetShelfUseCase(shelf_repo, section_repo, bookcase_repo).execute(shelf_id, UUID(payload["family_id"]))


@router.patch("/{shelf_id}", response_model=ShelfResponse, summary="Update shelf")
async def update_shelf(
	shelf_id: UUID,
	request: ShelfUpdate,
	payload: dict = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	shelf_repo = Depends(get_shelf_repository),
	section_repo = Depends(get_section_repository),
	bookcase_repo = Depends(get_bookcase_repository),
):
	updated = await UpdateShelfUseCase(shelf_repo, section_repo, bookcase_repo).execute(
		UpdateShelfInput(shelf_id=shelf_id, family_id=UUID(payload["family_id"]), **request.model_dump(exclude_unset=True))
	)
	await db.commit()
	return updated


@router.delete("/{shelf_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete shelf")
async def delete_shelf(
	shelf_id: UUID,
	payload: dict = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	shelf_repo = Depends(get_shelf_repository),
	section_repo = Depends(get_section_repository),
	bookcase_repo = Depends(get_bookcase_repository),
):
	await DeleteShelfUseCase(shelf_repo, section_repo, bookcase_repo).execute(shelf_id, UUID(payload["family_id"]))
	await db.commit()
