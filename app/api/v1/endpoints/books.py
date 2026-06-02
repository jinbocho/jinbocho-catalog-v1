from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Query, status
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
from app.api.v1.schemas.book_schemas import OwnedBookCreate, OwnedBookResponse, OwnedBookUpdate
from app.application.use_cases import (
	AddBookInput,
	AddBookUseCase,
	DeleteBookInput,
	DeleteBookUseCase,
	GetBookHistoryUseCase,
	GetOwnedBookUseCase,
	ListOwnedBooksUseCase,
	UpdateBookMetadataInput,
	UpdateBookMetadataUseCase,
	UpdateBookPositionInput,
	UpdateBookPositionUseCase,
	UpdateReadingStatusInput,
	UpdateReadingStatusUseCase,
)
from app.infrastructure.database.session import get_db

router = APIRouter(tags=["books"])


@router.get("/", response_model=list[OwnedBookResponse], summary="List owned books")
async def list_books(
	limit: int = Query(default=50, ge=1, le=200),
	offset: int = Query(default=0, ge=0),
	payload: dict = Depends(get_current_user_payload),
	book_repo = Depends(get_owned_book_repository),
):
	return await ListOwnedBooksUseCase(book_repo).execute(UUID(payload["family_id"]), limit, offset)


@router.post("/", response_model=OwnedBookResponse, status_code=status.HTTP_201_CREATED, summary="Add book")
async def add_book(
	request: OwnedBookCreate,
	payload: dict = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	book_repo = Depends(get_owned_book_repository),
	record_repo = Depends(get_bibliographic_record_repository),
	history_repo = Depends(get_book_history_repository),
	cache_repo = Depends(get_isbn_lookup_cache_repository),
	room_repo = Depends(get_room_repository),
	bookcase_repo = Depends(get_bookcase_repository),
	section_repo = Depends(get_section_repository),
	shelf_repo = Depends(get_shelf_repository),
	http_client: httpx.AsyncClient = Depends(get_http_client),
):
	book = await AddBookUseCase(record_repo, book_repo, history_repo, cache_repo, room_repo, bookcase_repo, section_repo, shelf_repo, http_client).execute(
		AddBookInput(family_id=UUID(payload["family_id"]), changed_by=UUID(payload["user_id"]), **request.model_dump())
	)
	await db.commit()
	return book


@router.get("/{book_id}", response_model=OwnedBookResponse, summary="Get book")
async def get_book(
	book_id: UUID,
	payload: dict = Depends(get_current_user_payload),
	book_repo = Depends(get_owned_book_repository),
):
	return await GetOwnedBookUseCase(book_repo).execute(book_id, UUID(payload["family_id"]))


@router.patch("/{book_id}", response_model=OwnedBookResponse, summary="Update book metadata")
async def update_book(
	book_id: UUID,
	request: OwnedBookUpdate,
	payload: dict = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	book_repo = Depends(get_owned_book_repository),
):
	updated = await UpdateBookMetadataUseCase(book_repo).execute(
		UpdateBookMetadataInput(book_id=book_id, family_id=UUID(payload["family_id"]), changed_by=UUID(payload["user_id"]), **request.model_dump(exclude_unset=True))
	)
	await db.commit()
	return updated


@router.post("/{book_id}/position", response_model=OwnedBookResponse, summary="Update book position")
async def update_book_position(
	book_id: UUID,
	room_id: UUID | None = None,
	bookcase_id: UUID | None = None,
	section_id: UUID | None = None,
	shelf_id: UUID | None = None,
	shelf_position: int | None = None,
	payload: dict = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	book_repo = Depends(get_owned_book_repository),
	history_repo = Depends(get_book_history_repository),
	room_repo = Depends(get_room_repository),
	bookcase_repo = Depends(get_bookcase_repository),
	section_repo = Depends(get_section_repository),
	shelf_repo = Depends(get_shelf_repository),
):
	updated = await UpdateBookPositionUseCase(book_repo, history_repo, room_repo, bookcase_repo, section_repo, shelf_repo).execute(
		UpdateBookPositionInput(book_id=book_id, family_id=UUID(payload["family_id"]), changed_by=UUID(payload["user_id"]),
			room_id=room_id, bookcase_id=bookcase_id, section_id=section_id, shelf_id=shelf_id, shelf_position=shelf_position,
			position_description=None)
	)
	await db.commit()
	return updated


@router.post("/{book_id}/reading-status", response_model=OwnedBookResponse, summary="Update reading status")
async def update_reading_status(
	book_id: UUID,
	reading_status: str,
	payload: dict = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	book_repo = Depends(get_owned_book_repository),
	history_repo = Depends(get_book_history_repository),
):
	updated = await UpdateReadingStatusUseCase(book_repo, history_repo).execute(
		UpdateReadingStatusInput(book_id=book_id, family_id=UUID(payload["family_id"]), changed_by=UUID(payload["user_id"]), reading_status=reading_status)
	)
	await db.commit()
	return updated


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete book")
async def delete_book(
	book_id: UUID,
	payload: dict = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	book_repo = Depends(get_owned_book_repository),
	history_repo = Depends(get_book_history_repository),
):
	await DeleteBookUseCase(book_repo, history_repo).execute(
		DeleteBookInput(book_id=book_id, family_id=UUID(payload["family_id"]), changed_by=UUID(payload["user_id"]))
	)
	await db.commit()


@router.get("/{book_id}/history", summary="Get book history")
async def get_book_history(
	book_id: UUID,
	payload: dict = Depends(get_current_user_payload),
	history_repo = Depends(get_book_history_repository),
	book_repo = Depends(get_owned_book_repository),
):
	return await GetBookHistoryUseCase(history_repo, book_repo).execute(book_id, UUID(payload["family_id"]))
