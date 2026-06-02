from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_payload, get_room_repository, require_role
from app.api.v1.schemas.room_schemas import RoomCreate, RoomResponse, RoomUpdate
from app.application.use_cases import CreateRoomInput, CreateRoomUseCase, DeleteRoomUseCase, GetRoomUseCase, ListRoomsUseCase, UpdateRoomInput, UpdateRoomUseCase
from app.infrastructure.database.session import get_db

router = APIRouter(tags=["rooms"])


@router.get(
	"/",
	response_model=list[RoomResponse],
	summary="List rooms",
	description="Retrieve all rooms for the family",
)
async def list_rooms(
	limit: int = Query(default=50, ge=1, le=200),
	offset: int = Query(default=0, ge=0),
	payload: dict = Depends(get_current_user_payload),
	room_repo = Depends(get_room_repository),
):
	return await ListRoomsUseCase(room_repo).execute(UUID(payload["family_id"]), limit, offset)


@router.post(
	"/",
	response_model=RoomResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Create room",
	description="Create a new room",
)
async def create_room(
	request: RoomCreate,
	payload: dict = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	room_repo = Depends(get_room_repository),
):
	room = await CreateRoomUseCase(room_repo).execute(CreateRoomInput(UUID(payload["family_id"]), request.name, request.description))
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
	payload: dict = Depends(get_current_user_payload),
	room_repo = Depends(get_room_repository),
):
	return await GetRoomUseCase(room_repo).execute(room_id, UUID(payload["family_id"]))


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
	payload: dict = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	room_repo = Depends(get_room_repository),
):
	updated = await UpdateRoomUseCase(room_repo).execute(
		UpdateRoomInput(room_id=room_id, family_id=UUID(payload["family_id"]), **request.model_dump(exclude_unset=True))
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
	payload: dict = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	room_repo = Depends(get_room_repository),
):
	await DeleteRoomUseCase(room_repo).execute(room_id, UUID(payload["family_id"]))
	await db.commit()
