from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db
from app.infrastructure.models import BookcaseModel, SectionModel, ShelfModel

router = APIRouter()


class BookcaseCreate(BaseModel):
    family_id: UUID
    room_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    type: str | None = None
    notes: str | None = None
    image_url: str | None = None


class BookcaseUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    type: str | None = None
    notes: str | None = None
    image_url: str | None = None
    room_id: UUID | None = None


class BookcaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    family_id: UUID
    room_id: UUID
    name: str
    description: str | None = None
    type: str | None = None
    notes: str | None = None
    image_url: str | None = None


@router.get("/", response_model=list[BookcaseResponse])
async def list_bookcases(room_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BookcaseModel).where(BookcaseModel.room_id == room_id).order_by(BookcaseModel.name))
    return result.scalars().all()


@router.post("/", response_model=BookcaseResponse, status_code=status.HTTP_201_CREATED)
async def create_bookcase(request: BookcaseCreate, db: AsyncSession = Depends(get_db)):
    bookcase = BookcaseModel(**request.model_dump())
    db.add(bookcase)
    await db.commit()
    await db.refresh(bookcase)
    return bookcase


@router.get("/{bookcase_id}", response_model=BookcaseResponse)
async def get_bookcase(bookcase_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BookcaseModel).where(BookcaseModel.id == bookcase_id))
    bookcase = result.scalar_one_or_none()
    if not bookcase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookcase not found")
    return bookcase


@router.patch("/{bookcase_id}", response_model=BookcaseResponse)
async def update_bookcase(bookcase_id: UUID, request: BookcaseUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BookcaseModel).where(BookcaseModel.id == bookcase_id))
    bookcase = result.scalar_one_or_none()
    if not bookcase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookcase not found")
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(bookcase, field, value)
    bookcase.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(bookcase)
    return bookcase


@router.delete("/{bookcase_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookcase(bookcase_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BookcaseModel).where(BookcaseModel.id == bookcase_id))
    bookcase = result.scalar_one_or_none()
    if not bookcase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookcase not found")
    await db.delete(bookcase)
    await db.commit()


@router.get("/{bookcase_id}/map")
async def get_bookcase_map(bookcase_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BookcaseModel).where(BookcaseModel.id == bookcase_id))
    bookcase = result.scalar_one_or_none()
    if not bookcase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookcase not found")

    sections_result = await db.execute(
        select(SectionModel).where(SectionModel.bookcase_id == bookcase_id).order_by(SectionModel.section_index)
    )
    sections = sections_result.scalars().all()
    section_ids = [section.id for section in sections]
    if section_ids:
        shelves_result = await db.execute(select(ShelfModel).where(ShelfModel.section_id.in_(section_ids)).order_by(ShelfModel.shelf_index))
        shelf_items = shelves_result.scalars().all()
    else:
        shelf_items = []
    shelves_by_section = {}
    for shelf in shelf_items:
        shelves_by_section.setdefault(str(shelf.section_id), []).append(
            {
                "id": str(shelf.id),
                "shelf_index": shelf.shelf_index,
                "notes": shelf.notes,
            }
        )

    return {
        "bookcase_id": str(bookcase.id),
        "name": bookcase.name,
        "image_url": bookcase.image_url,
        "sections": [
            {
                "id": str(section.id),
                "section_index": section.section_index,
                "label": section.label,
                "shelves": shelves_by_section.get(str(section.id), []),
            }
            for section in sections
        ],
    }
