from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_payload, get_room_repository, require_role
from app.api.v1.schemas.room_schemas import RoomCreate, RoomResponse, RoomUpdate
from app.application.use_cases import (
	CreateRoomInput,
	CreateRoomUseCase,
	DeleteRoomUseCase,
	GetRoomUseCase,
	ListRoomsUseCase,
	UpdateRoomInput,
	UpdateRoomUseCase,
)
from app.domain.entities import Room
from app.domain.repositories import RoomRepository
from app.infrastructure.database.session import get_db

router = APIRouter(tags=["rooms"])


@router.get(
	"/",
	response_model=list[RoomResponse],
	summary="List rooms",
	description="Retrieve all rooms for the library",
)
async def list_rooms(
	limit: int = Query(default=50, ge=1, le=200),
	offset: int = Query(default=0, ge=0),
	payload: dict[str, Any] = Depends(get_current_user_payload),
	room_repo: RoomRepository = Depends(get_room_repository),
) -> list[Room]:
	return await ListRoomsUseCase(room_repo).execute(UUID(payload["library_id"]), limit, offset)


@router.post(
	"/",
	response_model=RoomResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Create room",
	description="Create a new room",
)
async def create_room(
	request: RoomCreate,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	room_repo: RoomRepository = Depends(get_room_repository),
) -> Room:
	room = await CreateRoomUseCase(room_repo).execute(
		CreateRoomInput(UUID(payload["library_id"]), request.name, request.description)
	)
	await db.commit()
	return room


@router.get(
	"/{room_id}",
	response_model=RoomResponse,
	summary="Get room",
	description="Retrieve a specific room",
	responses={404: {"detail": "Room not found"}, 403: {"detail": "Access denied"}},
)
async def get_room(
	room_id: UUID,
	payload: dict[str, Any] = Depends(get_current_user_payload),
	room_repo: RoomRepository = Depends(get_room_repository),
) -> Room:
	return await GetRoomUseCase(room_repo).execute(room_id, UUID(payload["library_id"]))


@router.patch(
	"/{room_id}",
	response_model=RoomResponse,
	summary="Update room",
	description="Update room details",
	responses={404: {"detail": "Room not found"}, 403: {"detail": "Access denied"}},
)
async def update_room(
	room_id: UUID,
	request: RoomUpdate,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	room_repo: RoomRepository = Depends(get_room_repository),
) -> Room:
	updated = await UpdateRoomUseCase(room_repo).execute(
		UpdateRoomInput(
			room_id=room_id, library_id=UUID(payload["library_id"]), **request.model_dump(exclude_unset=True)
		)
	)
	await db.commit()
	return updated


@router.delete(
	"/{room_id}",
	status_code=status.HTTP_204_NO_CONTENT,
	summary="Delete room",
	description="Delete a room",
	responses={404: {"detail": "Room not found"}, 403: {"detail": "Access denied"}, 409: {"detail": "Cannot delete"}},
)
async def delete_room(
	room_id: UUID,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	room_repo: RoomRepository = Depends(get_room_repository),
) -> None:
	await DeleteRoomUseCase(room_repo).execute(room_id, UUID(payload["library_id"]))
	await db.commit()
