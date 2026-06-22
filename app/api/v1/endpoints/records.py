from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
	get_bibliographic_record_repository,
	get_current_user_payload,
	get_isbn_lookup_cache_repository,
	get_owned_book_repository,
	require_role,
)
from app.api.v1.schemas.record_schemas import (
	BibliographicRecordCreate,
	BibliographicRecordResponse,
	BibliographicRecordUpdate,
	GenreCountResponse,
	IncipitResponse,
	IncipitSetRequest,
)
from app.application.use_cases import (
	CreateBibliographicRecordInput,
	CreateBibliographicRecordUseCase,
	DeleteBibliographicRecordUseCase,
	GenreCount,
	GetBibliographicRecordUseCase,
	GetOrFetchIncipitUseCase,
	ListBibliographicRecordsUseCase,
	ListGenresUseCase,
	SetIncipitUseCase,
	UpdateBibliographicRecordInput,
	UpdateBibliographicRecordUseCase,
)
from app.domain.entities import BibliographicRecord, Genre
from app.domain.repositories import BibliographicRecordRepository, IsbnLookupCacheRepository, OwnedBookRepository
from app.infrastructure.database.session import get_db

router = APIRouter(tags=["records"])


@router.get("/", response_model=list[BibliographicRecordResponse], summary="Search bibliographic records")
async def list_records(
	q: str | None = Query(None, description="Search query"),
	genre: Genre | None = Query(None, description="Filter by normalized genre code"),
	limit: int = Query(default=50, ge=1, le=200),
	offset: int = Query(default=0, ge=0),
	payload: dict[str, Any] = Depends(get_current_user_payload),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
) -> list[BibliographicRecord]:
	return await ListBibliographicRecordsUseCase(record_repo).execute(
		UUID(payload["family_id"]), q, genre.value if genre else None, limit, offset
	)


@router.get("/genres", response_model=list[GenreCountResponse], summary="List genres present in the family library")
async def list_genres(
	payload: dict[str, Any] = Depends(get_current_user_payload),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
) -> list[GenreCount]:
	return await ListGenresUseCase(record_repo).execute(UUID(payload["family_id"]))


@router.post(
	"/",
	response_model=BibliographicRecordResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Create bibliographic record",
)
async def create_record(
	request: BibliographicRecordCreate,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
) -> BibliographicRecord:
	created = await CreateBibliographicRecordUseCase(record_repo).execute(
		CreateBibliographicRecordInput(family_id=UUID(payload["family_id"]), **request.model_dump())
	)
	await db.commit()
	return created


@router.get("/{record_id}", response_model=BibliographicRecordResponse, summary="Get bibliographic record")
async def get_record(
	record_id: UUID,
	payload: dict[str, Any] = Depends(get_current_user_payload),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
) -> BibliographicRecord:
	return await GetBibliographicRecordUseCase(record_repo).execute(record_id, UUID(payload["family_id"]))


@router.get("/{record_id}/incipit", response_model=IncipitResponse, summary="Get or lazily derive the book presentation")
async def get_incipit(
	record_id: UUID,
	payload: dict[str, Any] = Depends(get_current_user_payload),
	db: AsyncSession = Depends(get_db),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
	cache_repo: IsbnLookupCacheRepository = Depends(get_isbn_lookup_cache_repository),
) -> IncipitResponse:
	result = await GetOrFetchIncipitUseCase(record_repo, cache_repo).execute(record_id, UUID(payload["family_id"]))
	await db.commit()
	return IncipitResponse(text=result.text, source=result.source, generated_at=result.generated_at)


@router.put("/{record_id}/incipit", response_model=IncipitResponse, summary="Set the book presentation (manual or AI)")
async def set_incipit(
	record_id: UUID,
	request: IncipitSetRequest,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
) -> IncipitResponse:
	result = await SetIncipitUseCase(record_repo).execute(
		record_id, UUID(payload["family_id"]), request.text, request.source
	)
	await db.commit()
	return IncipitResponse(text=result.text, source=result.source, generated_at=result.generated_at)


@router.patch("/{record_id}", response_model=BibliographicRecordResponse, summary="Update bibliographic record")
async def update_record(
	record_id: UUID,
	request: BibliographicRecordUpdate,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
) -> BibliographicRecord:
	updated = await UpdateBibliographicRecordUseCase(record_repo).execute(
		UpdateBibliographicRecordInput(
			record_id=record_id, family_id=UUID(payload["family_id"]), **request.model_dump(exclude_unset=True)
		)
	)
	await db.commit()
	return updated


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete bibliographic record")
async def delete_record(
	record_id: UUID,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
) -> None:
	await DeleteBibliographicRecordUseCase(record_repo, book_repo).execute(record_id, UUID(payload["family_id"]))
	await db.commit()
