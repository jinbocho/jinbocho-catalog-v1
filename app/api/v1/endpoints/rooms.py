from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_payload, get_room_repository, require_role
from app.application.use_cases import CreateRoomInput, CreateRoomUseCase, DeleteRoomUseCase, GetRoomUseCase, ListRoomsUseCase, UpdateRoomInput, UpdateRoomUseCase
from app.domain.repositories import RoomRepository
from app.infrastructure.database.session import get_db

router = APIRouter()


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class RoomUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    family_id: UUID
    name: str
    description: str | None = None


@router.get("/", response_model=list[RoomResponse])
async def list_rooms(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    payload: dict = Depends(get_current_user_payload),
    room_repo: RoomRepository = Depends(get_room_repository),
):
    return await ListRoomsUseCase(room_repo).execute(UUID(payload["family_id"]), limit, offset)


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    request: RoomCreate,
    payload: dict = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
    room_repo: RoomRepository = Depends(get_room_repository),
):
    room = await CreateRoomUseCase(room_repo).execute(CreateRoomInput(UUID(payload["family_id"]), request.name, request.description))
    await db.commit()
    return room


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: UUID,
    payload: dict = Depends(get_current_user_payload),
    room_repo: RoomRepository = Depends(get_room_repository),
):
    try:
        return await GetRoomUseCase(room_repo).execute(room_id, UUID(payload["family_id"]))
    except LookupError:
        raise HTTPException(status_code=404, detail="Room not found")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.patch("/{room_id}", response_model=RoomResponse)
async def update_room(
    room_id: UUID,
    request: RoomUpdate,
    payload: dict = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
    room_repo: RoomRepository = Depends(get_room_repository),
):
    try:
        updated = await UpdateRoomUseCase(room_repo).execute(
            UpdateRoomInput(room_id=room_id, family_id=UUID(payload["family_id"]), **request.model_dump(exclude_unset=True))
        )
        await db.commit()
        return updated
    except LookupError:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Room not found")
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(exc))


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: UUID,
    payload: dict = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
    room_repo: RoomRepository = Depends(get_room_repository),
):
    try:
        await DeleteRoomUseCase(room_repo).execute(room_id, UUID(payload["family_id"]))
        await db.commit()
    except LookupError:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Room not found")
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(exc))
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Room cannot be deleted because it has bookcases. Remove them first.")
