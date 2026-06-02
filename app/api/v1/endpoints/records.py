from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_bibliographic_record_repository, get_current_user_payload, get_owned_book_repository, require_role
from app.api.v1.schemas.record_schemas import BibliographicRecordCreate, BibliographicRecordResponse, BibliographicRecordUpdate
from app.application.use_cases import (
	CreateBibliographicRecordInput,
	CreateBibliographicRecordUseCase,
	DeleteBibliographicRecordUseCase,
	GetBibliographicRecordUseCase,
	ListBibliographicRecordsUseCase,
	UpdateBibliographicRecordInput,
	UpdateBibliographicRecordUseCase,
)
from app.infrastructure.database.session import get_db

router = APIRouter(tags=["records"])


@router.get("/", response_model=list[BibliographicRecordResponse], summary="Search bibliographic records")
async def list_records(
	q: str | None = Query(None, description="Search query"),
	limit: int = Query(default=50, ge=1, le=200),
	offset: int = Query(default=0, ge=0),
	payload: dict = Depends(get_current_user_payload),
	record_repo = Depends(get_bibliographic_record_repository),
):
	return await ListBibliographicRecordsUseCase(record_repo).execute(UUID(payload["family_id"]), q, limit, offset)


@router.post("/", response_model=BibliographicRecordResponse, status_code=status.HTTP_201_CREATED, summary="Create bibliographic record")
async def create_record(
	request: BibliographicRecordCreate,
	payload: dict = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	record_repo = Depends(get_bibliographic_record_repository),
):
	created = await CreateBibliographicRecordUseCase(record_repo).execute(
		CreateBibliographicRecordInput(family_id=UUID(payload["family_id"]), **request.model_dump())
	)
	await db.commit()
	return created


@router.get("/{record_id}", response_model=BibliographicRecordResponse, summary="Get bibliographic record")
async def get_record(
	record_id: UUID,
	payload: dict = Depends(get_current_user_payload),
	record_repo = Depends(get_bibliographic_record_repository),
):
	return await GetBibliographicRecordUseCase(record_repo).execute(record_id, UUID(payload["family_id"]))


@router.patch("/{record_id}", response_model=BibliographicRecordResponse, summary="Update bibliographic record")
async def update_record(
	record_id: UUID,
	request: BibliographicRecordUpdate,
	payload: dict = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	record_repo = Depends(get_bibliographic_record_repository),
):
	updated = await UpdateBibliographicRecordUseCase(record_repo).execute(
		UpdateBibliographicRecordInput(record_id=record_id, family_id=UUID(payload["family_id"]), **request.model_dump(exclude_unset=True))
	)
	await db.commit()
	return updated


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete bibliographic record")
async def delete_record(
	record_id: UUID,
	payload: dict = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	record_repo = Depends(get_bibliographic_record_repository),
	book_repo = Depends(get_owned_book_repository),
):
	await DeleteBibliographicRecordUseCase(record_repo, book_repo).execute(record_id, UUID(payload["family_id"]))
	await db.commit()
