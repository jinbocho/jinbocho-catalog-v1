from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_bookcase_repository, get_current_user_payload, get_room_repository, require_role
from app.api.v1.schemas.bookcase_schemas import BookcaseCreate, BookcaseResponse, BookcaseUpdate
from app.application.use_cases import (
	CreateBookcaseInput,
	CreateBookcaseUseCase,
	DeleteBookcaseUseCase,
	GetBookcaseUseCase,
	ListBookcasesUseCase,
	UpdateBookcaseInput,
	UpdateBookcaseUseCase,
)
from app.domain.entities import Bookcase
from app.domain.repositories import BookcaseRepository, RoomRepository
from app.infrastructure.database.session import get_db

router = APIRouter(tags=["bookcases"])


@router.get("/", response_model=list[BookcaseResponse], summary="List bookcases")
async def list_bookcases(
	room_id: UUID | None = None,
	limit: int = Query(default=50, ge=1, le=200),
	offset: int = Query(default=0, ge=0),
	payload: dict[str, Any] = Depends(get_current_user_payload),
	bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
	room_repo: RoomRepository = Depends(get_room_repository),
) -> list[Bookcase]:
	return await ListBookcasesUseCase(bookcase_repo, room_repo).execute(
		UUID(payload["library_id"]), room_id, limit, offset
	)


@router.post("/", response_model=BookcaseResponse, status_code=status.HTTP_201_CREATED, summary="Create bookcase")
async def create_bookcase(
	request: BookcaseCreate,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
	room_repo: RoomRepository = Depends(get_room_repository),
) -> Bookcase:
	created = await CreateBookcaseUseCase(bookcase_repo, room_repo).execute(
		CreateBookcaseInput(library_id=UUID(payload["library_id"]), **request.model_dump())
	)
	await db.commit()
	return created


@router.get("/{bookcase_id}", response_model=BookcaseResponse, summary="Get bookcase")
async def get_bookcase(
	bookcase_id: UUID,
	payload: dict[str, Any] = Depends(get_current_user_payload),
	bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
) -> Bookcase:
	return await GetBookcaseUseCase(bookcase_repo).execute(bookcase_id, UUID(payload["library_id"]))


@router.patch("/{bookcase_id}", response_model=BookcaseResponse, summary="Update bookcase")
async def update_bookcase(
	bookcase_id: UUID,
	request: BookcaseUpdate,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
	room_repo: RoomRepository = Depends(get_room_repository),
) -> Bookcase:
	updated = await UpdateBookcaseUseCase(bookcase_repo, room_repo).execute(
		UpdateBookcaseInput(
			bookcase_id=bookcase_id, library_id=UUID(payload["library_id"]), **request.model_dump(exclude_unset=True)
		)
	)
	await db.commit()
	return updated


@router.delete("/{bookcase_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete bookcase")
async def delete_bookcase(
	bookcase_id: UUID,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
) -> None:
	await DeleteBookcaseUseCase(bookcase_repo).execute(bookcase_id, UUID(payload["library_id"]))
	await db.commit()
