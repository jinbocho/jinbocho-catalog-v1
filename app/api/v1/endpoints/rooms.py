from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db
from app.infrastructure.models import RoomModel

router = APIRouter()


class RoomCreate(BaseModel):
    family_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class RoomUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    family_id: UUID
    name: str
    description: str | None = None


@router.get("/", response_model=list[RoomResponse])
async def list_rooms(family_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RoomModel).where(RoomModel.family_id == family_id).order_by(RoomModel.name))
    return result.scalars().all()


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(request: RoomCreate, db: AsyncSession = Depends(get_db)):
    room = RoomModel(**request.model_dump())
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(room_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RoomModel).where(RoomModel.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return room


@router.patch("/{room_id}", response_model=RoomResponse)
async def update_room(room_id: UUID, request: RoomUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RoomModel).where(RoomModel.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(room, field, value)
    room.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(room)
    return room


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(room_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RoomModel).where(RoomModel.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    await db.delete(room)
    await db.commit()
