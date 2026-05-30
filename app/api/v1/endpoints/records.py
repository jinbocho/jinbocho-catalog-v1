from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db
from app.infrastructure.models import BibliographicRecordModel

router = APIRouter()


class BibliographicRecordCreate(BaseModel):
    family_id: UUID
    title: str = Field(min_length=1, max_length=500)
    main_author: str | None = None
    other_authors: list[str] = []
    isbn: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    language: str | None = None
    genre: str | None = None
    cover_url: str | None = None
    notes: str | None = None


class BibliographicRecordUpdate(BaseModel):
    title: str | None = None
    main_author: str | None = None
    other_authors: list[str] | None = None
    isbn: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    language: str | None = None
    genre: str | None = None
    cover_url: str | None = None
    notes: str | None = None


class BibliographicRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    family_id: UUID
    title: str
    main_author: str | None = None
    other_authors: list[str] | None = None
    isbn: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    language: str | None = None
    genre: str | None = None
    cover_url: str | None = None
    notes: str | None = None


@router.get("/search", response_model=list[BibliographicRecordResponse])
async def search_records(q: str = Query(min_length=1), db: AsyncSession = Depends(get_db)):
    pattern = f"%{q}%"
    result = await db.execute(
        select(BibliographicRecordModel).where(
            or_(
                BibliographicRecordModel.title.ilike(pattern),
                BibliographicRecordModel.main_author.ilike(pattern),
                BibliographicRecordModel.isbn.ilike(pattern),
            )
        )
    )
    return result.scalars().all()


@router.get("/", response_model=list[BibliographicRecordResponse])
async def list_records(
    family_id: UUID | None = None,
    isbn: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(BibliographicRecordModel)
    if family_id is not None:
        query = query.where(BibliographicRecordModel.family_id == family_id)
    if isbn is not None:
        query = query.where(BibliographicRecordModel.isbn == isbn)
    result = await db.execute(query.order_by(BibliographicRecordModel.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=BibliographicRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_record(request: BibliographicRecordCreate, db: AsyncSession = Depends(get_db)):
    record = BibliographicRecordModel(
        **request.model_dump(exclude={"other_authors"}),
        other_authors=request.other_authors or None,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/{record_id}", response_model=BibliographicRecordResponse)
async def get_record(record_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BibliographicRecordModel).where(BibliographicRecordModel.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bibliographic record not found")
    return record


@router.patch("/{record_id}", response_model=BibliographicRecordResponse)
async def update_record(record_id: UUID, request: BibliographicRecordUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BibliographicRecordModel).where(BibliographicRecordModel.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bibliographic record not found")
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    record.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(record_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BibliographicRecordModel).where(BibliographicRecordModel.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bibliographic record not found")
    await db.delete(record)
    await db.commit()
