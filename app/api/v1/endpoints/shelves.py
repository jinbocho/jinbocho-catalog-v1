from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db
from app.infrastructure.models import ShelfModel

router = APIRouter()


class ShelfCreate(BaseModel):
    section_id: UUID
    shelf_index: int
    notes: str | None = None


class ShelfUpdate(BaseModel):
    shelf_index: int | None = None
    notes: str | None = None


class ShelfResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    section_id: UUID
    shelf_index: int
    notes: str | None = None


@router.get("/", response_model=list[ShelfResponse])
async def list_shelves(section_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ShelfModel).where(ShelfModel.section_id == section_id).order_by(ShelfModel.shelf_index)
    )
    return result.scalars().all()


@router.post("/", response_model=ShelfResponse, status_code=status.HTTP_201_CREATED)
async def create_shelf(request: ShelfCreate, db: AsyncSession = Depends(get_db)):
    shelf = ShelfModel(**request.model_dump())
    db.add(shelf)
    await db.commit()
    await db.refresh(shelf)
    return shelf


@router.get("/{shelf_id}", response_model=ShelfResponse)
async def get_shelf(shelf_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ShelfModel).where(ShelfModel.id == shelf_id))
    shelf = result.scalar_one_or_none()
    if not shelf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shelf not found")
    return shelf


@router.patch("/{shelf_id}", response_model=ShelfResponse)
async def update_shelf(shelf_id: UUID, request: ShelfUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ShelfModel).where(ShelfModel.id == shelf_id))
    shelf = result.scalar_one_or_none()
    if not shelf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shelf not found")
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(shelf, field, value)
    shelf.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(shelf)
    return shelf


@router.delete("/{shelf_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shelf(shelf_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ShelfModel).where(ShelfModel.id == shelf_id))
    shelf = result.scalar_one_or_none()
    if not shelf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shelf not found")
    await db.delete(shelf)
    await db.commit()
