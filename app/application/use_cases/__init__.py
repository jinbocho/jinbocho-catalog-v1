from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import BibliographicRecordModel, BookHistoryModel, OwnedBookModel


@dataclass
class AddBookWithPositionInput:
    family_id: UUID
    title: str
    main_author: str | None = None
    other_authors: list[str] = field(default_factory=list)
    isbn: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    language: str | None = None
    genre: str | None = None
    cover_url: str | None = None
    notes: str | None = None
    bibliographic_record_id: UUID | None = None
    room_id: UUID | None = None
    bookcase_id: UUID | None = None
    section_id: UUID | None = None
    shelf_id: UUID | None = None
    shelf_position: int | None = None
    position_description: str | None = None
    reading_status: str = "to_read"
    tags: list[str] = field(default_factory=list)
    changed_by: UUID | None = None


class AddBookWithPosition:
    async def execute(self, db: AsyncSession, input: AddBookWithPositionInput) -> OwnedBookModel:
        record = None
        if input.bibliographic_record_id:
            result = await db.execute(
                select(BibliographicRecordModel).where(BibliographicRecordModel.id == input.bibliographic_record_id)
            )
            record = result.scalar_one_or_none()
        elif input.isbn:
            result = await db.execute(
                select(BibliographicRecordModel).where(
                    BibliographicRecordModel.family_id == input.family_id,
                    BibliographicRecordModel.isbn == input.isbn,
                )
            )
            record = result.scalar_one_or_none()

        if record is None:
            record = BibliographicRecordModel(
                family_id=input.family_id,
                title=input.title,
                main_author=input.main_author,
                other_authors=input.other_authors or None,
                isbn=input.isbn,
                publisher=input.publisher,
                publication_year=input.publication_year,
                language=input.language,
                genre=input.genre,
                cover_url=input.cover_url,
                notes=input.notes,
            )
            db.add(record)
            await db.flush()

        book = OwnedBookModel(
            family_id=input.family_id,
            bibliographic_record_id=record.id,
            room_id=input.room_id,
            bookcase_id=input.bookcase_id,
            section_id=input.section_id,
            shelf_id=input.shelf_id,
            shelf_position=input.shelf_position,
            position_description=input.position_description,
            reading_status=input.reading_status,
            tags=input.tags or None,
            notes=input.notes,
        )
        db.add(book)
        await db.flush()

        db.add(
            BookHistoryModel(
                owned_book_id=book.id,
                event_type="created",
                changed_by=input.changed_by or book.family_id,
                new_data={
                    "room_id": str(book.room_id) if book.room_id else None,
                    "bookcase_id": str(book.bookcase_id) if book.bookcase_id else None,
                    "section_id": str(book.section_id) if book.section_id else None,
                    "shelf_id": str(book.shelf_id) if book.shelf_id else None,
                    "shelf_position": book.shelf_position,
                },
            )
        )
        await db.flush()
        await db.refresh(book)
        return book


@dataclass
class MoveBookInput:
    owned_book_id: UUID
    changed_by: UUID
    room_id: UUID | None = None
    bookcase_id: UUID | None = None
    section_id: UUID | None = None
    shelf_id: UUID | None = None
    shelf_position: int | None = None
    position_description: str | None = None


class MoveBook:
    async def execute(self, db: AsyncSession, input: MoveBookInput) -> OwnedBookModel | None:
        result = await db.execute(select(OwnedBookModel).where(OwnedBookModel.id == input.owned_book_id))
        book = result.scalar_one_or_none()
        if book is None:
            return None

        old_data = {
            "room_id": str(book.room_id) if book.room_id else None,
            "bookcase_id": str(book.bookcase_id) if book.bookcase_id else None,
            "section_id": str(book.section_id) if book.section_id else None,
            "shelf_id": str(book.shelf_id) if book.shelf_id else None,
            "shelf_position": book.shelf_position,
            "position_description": book.position_description,
        }
        book.room_id = input.room_id
        book.bookcase_id = input.bookcase_id
        book.section_id = input.section_id
        book.shelf_id = input.shelf_id
        book.shelf_position = input.shelf_position
        book.position_description = input.position_description
        book.updated_at = datetime.utcnow()

        db.add(
            BookHistoryModel(
                owned_book_id=book.id,
                event_type="position_changed",
                changed_by=input.changed_by,
                old_data=old_data,
                new_data={
                    "room_id": str(book.room_id) if book.room_id else None,
                    "bookcase_id": str(book.bookcase_id) if book.bookcase_id else None,
                    "section_id": str(book.section_id) if book.section_id else None,
                    "shelf_id": str(book.shelf_id) if book.shelf_id else None,
                    "shelf_position": book.shelf_position,
                    "position_description": book.position_description,
                },
            )
        )
        await db.flush()
        await db.refresh(book)
        return book


@dataclass
class LookupIsbnAndCreateRecordInput:
    family_id: UUID
    isbn: str
    metadata: dict[str, Any]


class LookupIsbnAndCreateRecord:
    async def execute(self, db: AsyncSession, input: LookupIsbnAndCreateRecordInput) -> BibliographicRecordModel:
        result = await db.execute(
            select(BibliographicRecordModel).where(
                BibliographicRecordModel.family_id == input.family_id,
                BibliographicRecordModel.isbn == input.isbn,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing

        record = BibliographicRecordModel(
            family_id=input.family_id,
            isbn=input.isbn,
            title=input.metadata.get("title") or input.isbn,
            main_author=input.metadata.get("main_author"),
            other_authors=input.metadata.get("other_authors"),
            publisher=input.metadata.get("publisher"),
            publication_year=input.metadata.get("publication_year"),
            language=input.metadata.get("language"),
            genre=input.metadata.get("genre"),
            cover_url=input.metadata.get("cover_url"),
            notes=input.metadata.get("notes"),
        )
        db.add(record)
        await db.flush()
        await db.refresh(record)
        return record
