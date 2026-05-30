from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db
from app.infrastructure.models import SectionModel

router = APIRouter()


class SectionCreate(BaseModel):
    bookcase_id: UUID
    section_index: int
    label: str | None = None


class SectionUpdate(BaseModel):
    section_index: int | None = None
    label: str | None = None


class SectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bookcase_id: UUID
    section_index: int
    label: str | None = None


@router.get("/", response_model=list[SectionResponse])
async def list_sections(bookcase_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SectionModel).where(SectionModel.bookcase_id == bookcase_id).order_by(SectionModel.section_index)
    )
    return result.scalars().all()


@router.post("/", response_model=SectionResponse, status_code=status.HTTP_201_CREATED)
async def create_section(request: SectionCreate, db: AsyncSession = Depends(get_db)):
    section = SectionModel(**request.model_dump())
    db.add(section)
    await db.commit()
    await db.refresh(section)
    return section


@router.get("/{section_id}", response_model=SectionResponse)
async def get_section(section_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SectionModel).where(SectionModel.id == section_id))
    section = result.scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    return section


@router.patch("/{section_id}", response_model=SectionResponse)
async def update_section(section_id: UUID, request: SectionUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SectionModel).where(SectionModel.id == section_id))
    section = result.scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(section, field, value)
    section.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(section)
    return section


@router.delete("/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(section_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SectionModel).where(SectionModel.id == section_id))
    section = result.scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    await db.delete(section)
    await db.commit()
