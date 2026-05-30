import asyncio
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

import httpx

from app.config import settings
from app.domain.entities import BibliographicRecord, BookHistory, Bookcase, IsbnLookupCache, OwnedBook, Room, Section, Shelf
from app.domain.repositories import (
    BibliographicRecordRepository,
    BookHistoryRepository,
    BookcaseRepository,
    IsbnLookupCacheRepository,
    OwnedBookRepository,
    RoomRepository,
    SectionRepository,
    ShelfRepository,
)
from app.utils import utcnow

logger = logging.getLogger(__name__)


@dataclass
class LookupIsbnOutput:
    source: str
    metadata: dict[str, Any]
    cached: bool


class LookupIsbnUseCase:
    def __init__(self, cache_repo: IsbnLookupCacheRepository, http_client: Optional[httpx.AsyncClient] = None) -> None:
        self._cache_repo = cache_repo
        self._http_client = http_client

    async def execute(self, isbn: str) -> LookupIsbnOutput:
        cached = await self._cache_repo.find_by_isbn(isbn)
        if cached and cached.fetched_at >= utcnow() - timedelta(days=settings.isbn_cache_ttl_days):
            return LookupIsbnOutput(source=cached.source, metadata=cached.metadata, cached=True)

        if self._http_client is None:
            raise RuntimeError("HTTP client not configured")

        google = await self._fetch_google_books(isbn)
        if google:
            await self._cache_repo.save(
                IsbnLookupCache(isbn=isbn, metadata=google, source="google_books", fetched_at=utcnow())
            )
            return LookupIsbnOutput(source="google_books", metadata=google, cached=False)

        open_library = await self._fetch_open_library(isbn)
        if open_library:
            await self._cache_repo.save(
                IsbnLookupCache(isbn=isbn, metadata=open_library, source="open_library", fetched_at=utcnow())
            )
            return LookupIsbnOutput(source="open_library", metadata=open_library, cached=False)

        raise LookupError(f"No metadata found for ISBN {isbn}")

    async def _fetch_google_books(self, isbn: str) -> Optional[dict[str, Any]]:
        response = await self._http_client.get(
            f"{settings.google_books_url}/volumes",
            params={"q": f"isbn:{isbn}", "maxResults": 1},
        )
        if response.status_code in (429, 503):
            return None  # rate limited → fall through to Open Library
        response.raise_for_status()
        data = response.json()
        if not data.get("items"):
            return None
        volume = data["items"][0].get("volumeInfo", {})
        return {
            "title": volume.get("title"),
            "main_author": (volume.get("authors") or [None])[0],
            "other_authors": (volume.get("authors") or [])[1:],
            "publisher": volume.get("publisher"),
            "publication_year": _extract_year(volume.get("publishedDate")),
            "language": volume.get("language"),
            "genre": (volume.get("categories") or [None])[0],
            "cover_url": (volume.get("imageLinks") or {}).get("thumbnail"),
            "notes": volume.get("description"),
            "isbn": isbn,
        }

    async def _fetch_open_library(self, isbn: str) -> Optional[dict[str, Any]]:
        response = await self._http_client.get(
            f"{settings.open_library_url}/api/books",
            params={"bibkeys": f"ISBN:{isbn}", "format": "json", "jscmd": "data"},
        )
        response.raise_for_status()
        data = response.json()
        book = data.get(f"ISBN:{isbn}")
        if not book:
            return None
        authors = [author.get("name") for author in book.get("authors", []) if author.get("name")]
        publishers = [publisher.get("name") for publisher in book.get("publishers", []) if publisher.get("name")]
        return {
            "title": book.get("title"),
            "main_author": authors[0] if authors else None,
            "other_authors": authors[1:] if len(authors) > 1 else [],
            "publisher": publishers[0] if publishers else None,
            "publication_year": _extract_year(book.get("publish_date")),
            "language": None,
            "genre": None,
            "cover_url": (book.get("cover") or {}).get("medium") or (book.get("cover") or {}).get("large"),
            "notes": None,
            "isbn": isbn,
        }


@dataclass
class AddBookInput:
    family_id: UUID
    changed_by: UUID
    bibliographic_record_id: Optional[UUID] = None
    title: Optional[str] = None
    main_author: Optional[str] = None
    other_authors: list[str] | None = None
    isbn: Optional[str] = None
    publisher: Optional[str] = None
    publication_year: Optional[int] = None
    language: Optional[str] = None
    genre: Optional[str] = None
    cover_url: Optional[str] = None
    record_notes: Optional[str] = None
    notes: Optional[str] = None
    room_id: Optional[UUID] = None
    bookcase_id: Optional[UUID] = None
    section_id: Optional[UUID] = None
    shelf_id: Optional[UUID] = None
    shelf_position: Optional[int] = None
    position_description: Optional[str] = None
    condition: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_price: Optional[Decimal] = None
    source: Optional[str] = None
    reading_status: str = "to_read"
    tags: list[str] | None = None
    is_intentional_duplicate: bool = False
    duplicate_notes: Optional[str] = None


class AddBookUseCase:
    def __init__(
        self,
        record_repo: BibliographicRecordRepository,
        book_repo: OwnedBookRepository,
        history_repo: BookHistoryRepository,
        cache_repo: IsbnLookupCacheRepository,
        room_repo: RoomRepository,
        bookcase_repo: BookcaseRepository,
        section_repo: SectionRepository,
        shelf_repo: ShelfRepository,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._record_repo = record_repo
        self._book_repo = book_repo
        self._history_repo = history_repo
        self._cache_repo = cache_repo
        self._room_repo = room_repo
        self._bookcase_repo = bookcase_repo
        self._section_repo = section_repo
        self._shelf_repo = shelf_repo
        self._http_client = http_client

    async def execute(self, inp: AddBookInput) -> OwnedBook:
        await self._validate_position_ownership(inp)
        record = await self._resolve_bibliographic_record(inp)
        book = await self._book_repo.save(
            OwnedBook(
                family_id=inp.family_id,
                bibliographic_record_id=record.id,
                room_id=inp.room_id,
                bookcase_id=inp.bookcase_id,
                section_id=inp.section_id,
                shelf_id=inp.shelf_id,
                shelf_position=inp.shelf_position,
                position_description=inp.position_description,
                condition=inp.condition,
                purchase_date=inp.purchase_date,
                purchase_price=inp.purchase_price,
                source=inp.source,
                reading_status=inp.reading_status,
                tags=inp.tags or [],
                notes=inp.notes,
                is_intentional_duplicate=inp.is_intentional_duplicate,
                duplicate_notes=inp.duplicate_notes,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
        await self._history_repo.save(
            BookHistory(
                owned_book_id=book.id,
                event_type="created",
                changed_by=inp.changed_by,
                new_data={"reading_status": book.reading_status, "shelf_id": str(book.shelf_id) if book.shelf_id else None},
                created_at=utcnow(),
            )
        )
        return book

    async def _resolve_bibliographic_record(self, inp: AddBookInput) -> BibliographicRecord:
        if inp.bibliographic_record_id:
            record = await self._record_repo.find_by_id(inp.bibliographic_record_id)
            if record is None:
                raise LookupError(f"BibliographicRecord {inp.bibliographic_record_id} not found")
            if record.family_id != inp.family_id:
                raise PermissionError("BibliographicRecord belongs to a different family")
            return record

        if inp.isbn:
            existing = await self._record_repo.find_by_isbn(inp.family_id, inp.isbn)
            if existing:
                return existing

        metadata: dict[str, Any] = {
            "title": inp.title,
            "main_author": inp.main_author,
            "other_authors": inp.other_authors or [],
            "isbn": inp.isbn,
            "publisher": inp.publisher,
            "publication_year": inp.publication_year,
            "language": inp.language,
            "genre": inp.genre,
            "cover_url": inp.cover_url,
            "notes": inp.record_notes,
        }
        if inp.isbn and self._http_client is not None:
            try:
                cached = await self._cache_repo.find_by_isbn(inp.isbn)
                if cached and cached.fetched_at >= utcnow() - timedelta(days=settings.isbn_cache_ttl_days):
                    metadata = {**cached.metadata, **{k: v for k, v in metadata.items() if v is not None}}
                else:
                    lookup = LookupIsbnUseCase(self._cache_repo, self._http_client)
                    looked_up = await lookup.execute(inp.isbn)
                    metadata = {**looked_up.metadata, **{k: v for k, v in metadata.items() if v is not None}}
            except (httpx.HTTPError, asyncio.TimeoutError) as exc:
                logger.warning("ISBN lookup failed: %s", exc)

        title = metadata.get("title")
        if not title:
            raise ValueError("title is required when bibliographic_record_id is not provided")

        return await self._record_repo.save(
            BibliographicRecord(
                family_id=inp.family_id,
                title=title,
                main_author=metadata.get("main_author"),
                other_authors=list(metadata.get("other_authors") or []),
                isbn=metadata.get("isbn"),
                publisher=metadata.get("publisher"),
                publication_year=metadata.get("publication_year"),
                language=metadata.get("language"),
                genre=metadata.get("genre"),
                cover_url=metadata.get("cover_url"),
                notes=metadata.get("notes"),
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )

    async def _validate_position_ownership(self, inp: AddBookInput) -> None:
        resolved_room_id = inp.room_id
        resolved_bookcase_id = inp.bookcase_id
        resolved_section_id = inp.section_id

        if inp.shelf_id:
            shelf = await self._shelf_repo.find_by_id(inp.shelf_id)
            if shelf is None:
                raise LookupError("Shelf not found")
            section = await self._section_repo.find_by_id(shelf.section_id)
            if section is None:
                raise LookupError("Section not found")
            bookcase = await self._bookcase_repo.find_by_id(section.bookcase_id)
            if bookcase is None:
                raise LookupError("Bookcase not found")
            if bookcase.family_id != inp.family_id:
                raise PermissionError("Position entity belongs to a different family")
            resolved_section_id = shelf.section_id
            resolved_bookcase_id = section.bookcase_id
            resolved_room_id = bookcase.room_id
            if inp.section_id and inp.section_id != shelf.section_id:
                raise ValueError("shelf_id does not belong to the provided section_id")
            if inp.bookcase_id and inp.bookcase_id != section.bookcase_id:
                raise ValueError("section_id does not belong to the provided bookcase_id")
            if inp.room_id and inp.room_id != bookcase.room_id:
                raise ValueError("bookcase_id does not belong to the provided room_id")

        if resolved_section_id:
            section = await self._section_repo.find_by_id(resolved_section_id)
            if section is None:
                raise LookupError("Section not found")
            bookcase = await self._bookcase_repo.find_by_id(section.bookcase_id)
            if bookcase is None:
                raise LookupError("Bookcase not found")
            if bookcase.family_id != inp.family_id:
                raise PermissionError("Position entity belongs to a different family")
            resolved_bookcase_id = section.bookcase_id
            resolved_room_id = bookcase.room_id
            if inp.bookcase_id and inp.bookcase_id != section.bookcase_id:
                raise ValueError("section_id does not belong to the provided bookcase_id")
            if inp.room_id and inp.room_id != bookcase.room_id:
                raise ValueError("bookcase_id does not belong to the provided room_id")

        if resolved_bookcase_id:
            bookcase = await self._bookcase_repo.find_by_id(resolved_bookcase_id)
            if bookcase is None:
                raise LookupError("Bookcase not found")
            if bookcase.family_id != inp.family_id:
                raise PermissionError("Position entity belongs to a different family")
            resolved_room_id = bookcase.room_id
            if inp.room_id and inp.room_id != bookcase.room_id:
                raise ValueError("bookcase_id does not belong to the provided room_id")

        if resolved_room_id:
            room = await self._room_repo.find_by_id(resolved_room_id)
            if room is None:
                raise LookupError("Room not found")
            if room.family_id != inp.family_id:
                raise PermissionError("Position entity belongs to a different family")


@dataclass
class UpdateBookPositionInput:
    book_id: UUID
    family_id: UUID
    changed_by: UUID
    room_id: Optional[UUID]
    bookcase_id: Optional[UUID]
    section_id: Optional[UUID]
    shelf_id: Optional[UUID]
    shelf_position: Optional[int]
    position_description: Optional[str]


class UpdateBookPositionUseCase:
    def __init__(
        self,
        book_repo: OwnedBookRepository,
        history_repo: BookHistoryRepository,
        room_repo: RoomRepository,
        bookcase_repo: BookcaseRepository,
        section_repo: SectionRepository,
        shelf_repo: ShelfRepository,
    ) -> None:
        self._book_repo = book_repo
        self._history_repo = history_repo
        self._room_repo = room_repo
        self._bookcase_repo = bookcase_repo
        self._section_repo = section_repo
        self._shelf_repo = shelf_repo

    async def execute(self, inp: UpdateBookPositionInput) -> OwnedBook:
        book = await self._book_repo.find_by_id(inp.book_id)
        if book is None:
            raise LookupError(f"OwnedBook {inp.book_id} not found")
        if book.family_id != inp.family_id:
            raise PermissionError("Access denied")

        await self._validate_position_ownership(inp)
        old = {
            "room_id": str(book.room_id) if book.room_id else None,
            "bookcase_id": str(book.bookcase_id) if book.bookcase_id else None,
            "section_id": str(book.section_id) if book.section_id else None,
            "shelf_id": str(book.shelf_id) if book.shelf_id else None,
            "shelf_position": book.shelf_position,
            "position_description": book.position_description,
        }
        book.room_id = inp.room_id
        book.bookcase_id = inp.bookcase_id
        book.section_id = inp.section_id
        book.shelf_id = inp.shelf_id
        book.shelf_position = inp.shelf_position
        book.position_description = inp.position_description
        book.updated_at = utcnow()
        saved = await self._book_repo.save(book)
        await self._history_repo.save(
            BookHistory(
                owned_book_id=saved.id,
                event_type="position_changed",
                changed_by=inp.changed_by,
                old_data=old,
                new_data={
                    "room_id": str(saved.room_id) if saved.room_id else None,
                    "bookcase_id": str(saved.bookcase_id) if saved.bookcase_id else None,
                    "section_id": str(saved.section_id) if saved.section_id else None,
                    "shelf_id": str(saved.shelf_id) if saved.shelf_id else None,
                    "shelf_position": saved.shelf_position,
                    "position_description": saved.position_description,
                },
                created_at=utcnow(),
            )
        )
        return saved

    async def _validate_position_ownership(self, inp: UpdateBookPositionInput) -> None:
        resolved_room_id = inp.room_id
        resolved_bookcase_id = inp.bookcase_id
        resolved_section_id = inp.section_id

        if inp.shelf_id:
            shelf = await self._shelf_repo.find_by_id(inp.shelf_id)
            if shelf is None:
                raise LookupError("Shelf not found")
            section = await self._section_repo.find_by_id(shelf.section_id)
            if section is None:
                raise LookupError("Section not found")
            bookcase = await self._bookcase_repo.find_by_id(section.bookcase_id)
            if bookcase is None:
                raise LookupError("Bookcase not found")
            if bookcase.family_id != inp.family_id:
                raise PermissionError("Position entity belongs to a different family")
            resolved_section_id = shelf.section_id
            resolved_bookcase_id = section.bookcase_id
            resolved_room_id = bookcase.room_id
            if inp.section_id and inp.section_id != shelf.section_id:
                raise ValueError("shelf_id does not belong to the provided section_id")
            if inp.bookcase_id and inp.bookcase_id != section.bookcase_id:
                raise ValueError("section_id does not belong to the provided bookcase_id")
            if inp.room_id and inp.room_id != bookcase.room_id:
                raise ValueError("bookcase_id does not belong to the provided room_id")

        if resolved_section_id:
            section = await self._section_repo.find_by_id(resolved_section_id)
            if section is None:
                raise LookupError("Section not found")
            bookcase = await self._bookcase_repo.find_by_id(section.bookcase_id)
            if bookcase is None:
                raise LookupError("Bookcase not found")
            if bookcase.family_id != inp.family_id:
                raise PermissionError("Position entity belongs to a different family")
            resolved_bookcase_id = section.bookcase_id
            resolved_room_id = bookcase.room_id
            if inp.bookcase_id and inp.bookcase_id != section.bookcase_id:
                raise ValueError("section_id does not belong to the provided bookcase_id")
            if inp.room_id and inp.room_id != bookcase.room_id:
                raise ValueError("bookcase_id does not belong to the provided room_id")

        if resolved_bookcase_id:
            bookcase = await self._bookcase_repo.find_by_id(resolved_bookcase_id)
            if bookcase is None:
                raise LookupError("Bookcase not found")
            if bookcase.family_id != inp.family_id:
                raise PermissionError("Position entity belongs to a different family")
            resolved_room_id = bookcase.room_id
            if inp.room_id and inp.room_id != bookcase.room_id:
                raise ValueError("bookcase_id does not belong to the provided room_id")

        if resolved_room_id:
            room = await self._room_repo.find_by_id(resolved_room_id)
            if room is None:
                raise LookupError("Room not found")
            if room.family_id != inp.family_id:
                raise PermissionError("Position entity belongs to a different family")


@dataclass
class UpdateReadingStatusInput:
    book_id: UUID
    family_id: UUID
    changed_by: UUID
    reading_status: str


class UpdateReadingStatusUseCase:
    def __init__(self, book_repo: OwnedBookRepository, history_repo: BookHistoryRepository) -> None:
        self._book_repo = book_repo
        self._history_repo = history_repo

    async def execute(self, inp: UpdateReadingStatusInput) -> OwnedBook:
        book = await self._book_repo.find_by_id(inp.book_id)
        if book is None:
            raise LookupError(f"OwnedBook {inp.book_id} not found")
        if book.family_id != inp.family_id:
            raise PermissionError("Access denied")

        old_status = book.reading_status
        book.reading_status = inp.reading_status
        book.updated_at = utcnow()
        saved = await self._book_repo.save(book)
        await self._history_repo.save(
            BookHistory(
                owned_book_id=saved.id,
                event_type="reading_status_changed",
                changed_by=inp.changed_by,
                old_data={"reading_status": old_status},
                new_data={"reading_status": saved.reading_status},
                created_at=utcnow(),
            )
        )
        return saved


@dataclass
class DeleteBookInput:
    book_id: UUID
    family_id: UUID
    changed_by: UUID


class DeleteBookUseCase:
    def __init__(self, book_repo: OwnedBookRepository, history_repo: BookHistoryRepository) -> None:
        self._book_repo = book_repo
        self._history_repo = history_repo

    async def execute(self, inp: DeleteBookInput) -> None:
        book = await self._book_repo.find_by_id(inp.book_id)
        if book is None:
            raise LookupError(f"OwnedBook {inp.book_id} not found")
        if book.family_id != inp.family_id:
            raise PermissionError("Access denied")
        await self._history_repo.save(
            BookHistory(
                owned_book_id=book.id,
                event_type="deleted",
                changed_by=inp.changed_by,
                old_data={"bibliographic_record_id": str(book.bibliographic_record_id)},
                created_at=utcnow(),
            )
        )
        await self._book_repo.delete(book.id)


@dataclass
class CreateRoomInput:
    family_id: UUID
    name: str
    description: Optional[str] = None


@dataclass
class UpdateRoomInput:
    room_id: UUID
    family_id: UUID
    name: Optional[str] = None
    description: Optional[str] = None


class CreateRoomUseCase:
    def __init__(self, room_repo: RoomRepository) -> None:
        self._room_repo = room_repo

    async def execute(self, inp: CreateRoomInput) -> Room:
        return await self._room_repo.save(Room(family_id=inp.family_id, name=inp.name, description=inp.description))


class UpdateRoomUseCase:
    def __init__(self, room_repo: RoomRepository) -> None:
        self._room_repo = room_repo

    async def execute(self, inp: UpdateRoomInput) -> Room:
        room = await _get_room_for_family(self._room_repo, inp.room_id, inp.family_id)
        if inp.name is not None:
            room.name = inp.name
        if inp.description is not None:
            room.description = inp.description
        room.updated_at = utcnow()
        return await self._room_repo.save(room)


class DeleteRoomUseCase:
    def __init__(self, room_repo: RoomRepository) -> None:
        self._room_repo = room_repo

    async def execute(self, room_id: UUID, family_id: UUID) -> None:
        await _get_room_for_family(self._room_repo, room_id, family_id)
        await self._room_repo.delete(room_id)


class ListRoomsUseCase:
    def __init__(self, room_repo: RoomRepository) -> None:
        self._room_repo = room_repo

    async def execute(self, family_id: UUID, limit: int, offset: int) -> list[Room]:
        return await self._room_repo.find_all_by_family(family_id, limit=limit, offset=offset)


class GetRoomUseCase:
    def __init__(self, room_repo: RoomRepository) -> None:
        self._room_repo = room_repo

    async def execute(self, room_id: UUID, family_id: UUID) -> Room:
        return await _get_room_for_family(self._room_repo, room_id, family_id)


@dataclass
class CreateBookcaseInput:
    family_id: UUID
    room_id: UUID
    name: str
    description: Optional[str] = None
    type: Optional[str] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None


@dataclass
class UpdateBookcaseInput:
    bookcase_id: UUID
    family_id: UUID
    room_id: Optional[UUID] = None
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None


class CreateBookcaseUseCase:
    def __init__(self, bookcase_repo: BookcaseRepository, room_repo: RoomRepository) -> None:
        self._bookcase_repo = bookcase_repo
        self._room_repo = room_repo

    async def execute(self, inp: CreateBookcaseInput) -> Bookcase:
        await _get_room_for_family(self._room_repo, inp.room_id, inp.family_id)
        return await self._bookcase_repo.save(
            Bookcase(
                family_id=inp.family_id,
                room_id=inp.room_id,
                name=inp.name,
                description=inp.description,
                type=inp.type,
                notes=inp.notes,
                image_url=inp.image_url,
            )
        )


class UpdateBookcaseUseCase:
    def __init__(self, bookcase_repo: BookcaseRepository, room_repo: RoomRepository) -> None:
        self._bookcase_repo = bookcase_repo
        self._room_repo = room_repo

    async def execute(self, inp: UpdateBookcaseInput) -> Bookcase:
        bookcase = await _get_bookcase_for_family(self._bookcase_repo, inp.bookcase_id, inp.family_id)
        if inp.room_id is not None:
            await _get_room_for_family(self._room_repo, inp.room_id, inp.family_id)
            bookcase.room_id = inp.room_id
        if inp.name is not None:
            bookcase.name = inp.name
        if inp.description is not None:
            bookcase.description = inp.description
        if inp.type is not None:
            bookcase.type = inp.type
        if inp.notes is not None:
            bookcase.notes = inp.notes
        if inp.image_url is not None:
            bookcase.image_url = inp.image_url
        bookcase.updated_at = utcnow()
        return await self._bookcase_repo.save(bookcase)


class DeleteBookcaseUseCase:
    def __init__(self, bookcase_repo: BookcaseRepository) -> None:
        self._bookcase_repo = bookcase_repo

    async def execute(self, bookcase_id: UUID, family_id: UUID) -> None:
        await _get_bookcase_for_family(self._bookcase_repo, bookcase_id, family_id)
        await self._bookcase_repo.delete(bookcase_id)


class ListBookcasesUseCase:
    def __init__(self, bookcase_repo: BookcaseRepository, room_repo: RoomRepository) -> None:
        self._bookcase_repo = bookcase_repo
        self._room_repo = room_repo

    async def execute(self, family_id: UUID, room_id: Optional[UUID], limit: int, offset: int) -> list[Bookcase]:
        if room_id is not None:
            await _get_room_for_family(self._room_repo, room_id, family_id)
        return await self._bookcase_repo.find_all_by_family(family_id, room_id=room_id, limit=limit, offset=offset)


class GetBookcaseUseCase:
    def __init__(self, bookcase_repo: BookcaseRepository) -> None:
        self._bookcase_repo = bookcase_repo

    async def execute(self, bookcase_id: UUID, family_id: UUID) -> Bookcase:
        return await _get_bookcase_for_family(self._bookcase_repo, bookcase_id, family_id)


@dataclass
class CreateSectionInput:
    family_id: UUID
    bookcase_id: UUID
    section_index: int
    label: Optional[str] = None


@dataclass
class UpdateSectionInput:
    section_id: UUID
    family_id: UUID
    bookcase_id: Optional[UUID] = None
    section_index: Optional[int] = None
    label: Optional[str] = None


class CreateSectionUseCase:
    def __init__(self, section_repo: SectionRepository, bookcase_repo: BookcaseRepository) -> None:
        self._section_repo = section_repo
        self._bookcase_repo = bookcase_repo

    async def execute(self, inp: CreateSectionInput) -> Section:
        await _get_bookcase_for_family(self._bookcase_repo, inp.bookcase_id, inp.family_id)
        return await self._section_repo.save(
            Section(bookcase_id=inp.bookcase_id, section_index=inp.section_index, label=inp.label)
        )


class UpdateSectionUseCase:
    def __init__(self, section_repo: SectionRepository, bookcase_repo: BookcaseRepository) -> None:
        self._section_repo = section_repo
        self._bookcase_repo = bookcase_repo

    async def execute(self, inp: UpdateSectionInput) -> Section:
        section = await _get_section_for_family(self._section_repo, self._bookcase_repo, inp.section_id, inp.family_id)
        if inp.bookcase_id is not None:
            await _get_bookcase_for_family(self._bookcase_repo, inp.bookcase_id, inp.family_id)
            section.bookcase_id = inp.bookcase_id
        if inp.section_index is not None:
            section.section_index = inp.section_index
        if inp.label is not None:
            section.label = inp.label
        section.updated_at = utcnow()
        return await self._section_repo.save(section)


class DeleteSectionUseCase:
    def __init__(self, section_repo: SectionRepository, bookcase_repo: BookcaseRepository) -> None:
        self._section_repo = section_repo
        self._bookcase_repo = bookcase_repo

    async def execute(self, section_id: UUID, family_id: UUID) -> None:
        await _get_section_for_family(self._section_repo, self._bookcase_repo, section_id, family_id)
        await self._section_repo.delete(section_id)


class ListSectionsUseCase:
    def __init__(self, section_repo: SectionRepository, bookcase_repo: BookcaseRepository) -> None:
        self._section_repo = section_repo
        self._bookcase_repo = bookcase_repo

    async def execute(self, family_id: UUID, bookcase_id: Optional[UUID], limit: int, offset: int) -> list[Section]:
        if bookcase_id is not None:
            await _get_bookcase_for_family(self._bookcase_repo, bookcase_id, family_id)
        return await self._section_repo.find_all_by_family(family_id, bookcase_id=bookcase_id, limit=limit, offset=offset)


class GetSectionUseCase:
    def __init__(self, section_repo: SectionRepository, bookcase_repo: BookcaseRepository) -> None:
        self._section_repo = section_repo
        self._bookcase_repo = bookcase_repo

    async def execute(self, section_id: UUID, family_id: UUID) -> Section:
        return await _get_section_for_family(self._section_repo, self._bookcase_repo, section_id, family_id)


@dataclass
class CreateShelfInput:
    family_id: UUID
    section_id: UUID
    shelf_index: int
    notes: Optional[str] = None


@dataclass
class UpdateShelfInput:
    shelf_id: UUID
    family_id: UUID
    section_id: Optional[UUID] = None
    shelf_index: Optional[int] = None
    notes: Optional[str] = None


class CreateShelfUseCase:
    def __init__(self, shelf_repo: ShelfRepository, section_repo: SectionRepository, bookcase_repo: BookcaseRepository) -> None:
        self._shelf_repo = shelf_repo
        self._section_repo = section_repo
        self._bookcase_repo = bookcase_repo

    async def execute(self, inp: CreateShelfInput) -> Shelf:
        await _get_section_for_family(self._section_repo, self._bookcase_repo, inp.section_id, inp.family_id)
        return await self._shelf_repo.save(Shelf(section_id=inp.section_id, shelf_index=inp.shelf_index, notes=inp.notes))


class UpdateShelfUseCase:
    def __init__(self, shelf_repo: ShelfRepository, section_repo: SectionRepository, bookcase_repo: BookcaseRepository) -> None:
        self._shelf_repo = shelf_repo
        self._section_repo = section_repo
        self._bookcase_repo = bookcase_repo

    async def execute(self, inp: UpdateShelfInput) -> Shelf:
        shelf = await _get_shelf_for_family(self._shelf_repo, self._section_repo, self._bookcase_repo, inp.shelf_id, inp.family_id)
        if inp.section_id is not None:
            await _get_section_for_family(self._section_repo, self._bookcase_repo, inp.section_id, inp.family_id)
            shelf.section_id = inp.section_id
        if inp.shelf_index is not None:
            shelf.shelf_index = inp.shelf_index
        if inp.notes is not None:
            shelf.notes = inp.notes
        shelf.updated_at = utcnow()
        return await self._shelf_repo.save(shelf)


class DeleteShelfUseCase:
    def __init__(self, shelf_repo: ShelfRepository, section_repo: SectionRepository, bookcase_repo: BookcaseRepository) -> None:
        self._shelf_repo = shelf_repo
        self._section_repo = section_repo
        self._bookcase_repo = bookcase_repo

    async def execute(self, shelf_id: UUID, family_id: UUID) -> None:
        await _get_shelf_for_family(self._shelf_repo, self._section_repo, self._bookcase_repo, shelf_id, family_id)
        await self._shelf_repo.delete(shelf_id)


class ListShelvesUseCase:
    def __init__(self, shelf_repo: ShelfRepository, section_repo: SectionRepository, bookcase_repo: BookcaseRepository) -> None:
        self._shelf_repo = shelf_repo
        self._section_repo = section_repo
        self._bookcase_repo = bookcase_repo

    async def execute(self, family_id: UUID, section_id: Optional[UUID], limit: int, offset: int) -> list[Shelf]:
        if section_id is not None:
            await _get_section_for_family(self._section_repo, self._bookcase_repo, section_id, family_id)
        return await self._shelf_repo.find_all_by_family(family_id, section_id=section_id, limit=limit, offset=offset)


class GetShelfUseCase:
    def __init__(self, shelf_repo: ShelfRepository, section_repo: SectionRepository, bookcase_repo: BookcaseRepository) -> None:
        self._shelf_repo = shelf_repo
        self._section_repo = section_repo
        self._bookcase_repo = bookcase_repo

    async def execute(self, shelf_id: UUID, family_id: UUID) -> Shelf:
        return await _get_shelf_for_family(self._shelf_repo, self._section_repo, self._bookcase_repo, shelf_id, family_id)


@dataclass
class CreateBibliographicRecordInput:
    family_id: UUID
    title: str
    main_author: Optional[str] = None
    other_authors: list[str] | None = None
    isbn: Optional[str] = None
    publisher: Optional[str] = None
    publication_year: Optional[int] = None
    language: Optional[str] = None
    genre: Optional[str] = None
    cover_url: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class UpdateBibliographicRecordInput:
    record_id: UUID
    family_id: UUID
    title: Optional[str] = None
    main_author: Optional[str] = None
    other_authors: list[str] | None = None
    isbn: Optional[str] = None
    publisher: Optional[str] = None
    publication_year: Optional[int] = None
    language: Optional[str] = None
    genre: Optional[str] = None
    cover_url: Optional[str] = None
    notes: Optional[str] = None


class CreateBibliographicRecordUseCase:
    def __init__(self, record_repo: BibliographicRecordRepository) -> None:
        self._record_repo = record_repo

    async def execute(self, inp: CreateBibliographicRecordInput) -> BibliographicRecord:
        return await self._record_repo.save(
            BibliographicRecord(
                family_id=inp.family_id,
                title=inp.title,
                main_author=inp.main_author,
                other_authors=inp.other_authors or [],
                isbn=inp.isbn,
                publisher=inp.publisher,
                publication_year=inp.publication_year,
                language=inp.language,
                genre=inp.genre,
                cover_url=inp.cover_url,
                notes=inp.notes,
            )
        )


class UpdateBibliographicRecordUseCase:
    def __init__(self, record_repo: BibliographicRecordRepository) -> None:
        self._record_repo = record_repo

    async def execute(self, inp: UpdateBibliographicRecordInput) -> BibliographicRecord:
        record = await _get_record_for_family(self._record_repo, inp.record_id, inp.family_id)
        if inp.title is not None:
            record.title = inp.title
        if inp.main_author is not None:
            record.main_author = inp.main_author
        if inp.other_authors is not None:
            record.other_authors = inp.other_authors
        if inp.isbn is not None:
            record.isbn = inp.isbn
        if inp.publisher is not None:
            record.publisher = inp.publisher
        if inp.publication_year is not None:
            record.publication_year = inp.publication_year
        if inp.language is not None:
            record.language = inp.language
        if inp.genre is not None:
            record.genre = inp.genre
        if inp.cover_url is not None:
            record.cover_url = inp.cover_url
        if inp.notes is not None:
            record.notes = inp.notes
        record.updated_at = utcnow()
        return await self._record_repo.save(record)


class DeleteBibliographicRecordUseCase:
    def __init__(self, record_repo: BibliographicRecordRepository, book_repo: OwnedBookRepository) -> None:
        self._record_repo = record_repo
        self._book_repo = book_repo

    async def execute(self, record_id: UUID, family_id: UUID) -> None:
        await _get_record_for_family(self._record_repo, record_id, family_id)
        if await self._book_repo.exists_by_bibliographic_record_id(record_id):
            raise ValueError("Cannot delete a bibliographic record that is still referenced by owned books")
        await self._record_repo.delete(record_id)


class ListBibliographicRecordsUseCase:
    def __init__(self, record_repo: BibliographicRecordRepository) -> None:
        self._record_repo = record_repo

    async def execute(self, family_id: UUID, q: Optional[str], limit: int, offset: int) -> list[BibliographicRecord]:
        return await self._record_repo.find_all_by_family(family_id, q=q, limit=limit, offset=offset)


@dataclass
class ExportBookItem:
    book: OwnedBook
    record: BibliographicRecord | None


class ExportBooksUseCase:
    def __init__(self, book_repo: OwnedBookRepository, record_repo: BibliographicRecordRepository) -> None:
        self._book_repo = book_repo
        self._record_repo = record_repo

    async def execute(self, family_id: UUID, limit: int, offset: int) -> list[ExportBookItem]:
        books = await self._book_repo.find_all_by_family(family_id, limit=limit, offset=offset)
        record_map = {
            record.id: record
            for record in await self._record_repo.find_all_by_ids([book.bibliographic_record_id for book in books])
        }
        return [ExportBookItem(book=book, record=record_map.get(book.bibliographic_record_id)) for book in books]


@dataclass
class MapShelfBooks:
    shelf: Shelf
    books: list[ExportBookItem]


@dataclass
class MapSectionData:
    section: Section
    shelves: list[MapShelfBooks]


class GetBookcaseMapUseCase:
    def __init__(
        self,
        bookcase_repo: BookcaseRepository,
        section_repo: SectionRepository,
        shelf_repo: ShelfRepository,
        book_repo: OwnedBookRepository,
        record_repo: BibliographicRecordRepository,
    ) -> None:
        self._bookcase_repo = bookcase_repo
        self._section_repo = section_repo
        self._shelf_repo = shelf_repo
        self._book_repo = book_repo
        self._record_repo = record_repo

    async def execute(self, family_id: UUID, bookcase_id: UUID) -> tuple[Bookcase, list[MapSectionData]]:
        bookcase = await _get_bookcase_for_family(self._bookcase_repo, bookcase_id, family_id)
        sections = await self._section_repo.find_all_by_bookcase(bookcase_id, limit=200, offset=0)
        shelves_by_section: dict[UUID, list[Shelf]] = {}
        shelf_ids: list[UUID] = []
        for section in sections:
            section_shelves = await self._shelf_repo.find_all_by_section(section.id, limit=500, offset=0)
            shelves_by_section[section.id] = section_shelves
            shelf_ids.extend(shelf.id for shelf in section_shelves)

        books = await self._book_repo.find_all_by_shelf_ids(shelf_ids)
        records = await self._record_repo.find_all_by_ids([book.bibliographic_record_id for book in books])
        record_map = {record.id: record for record in records}
        books_by_shelf: dict[UUID, list[ExportBookItem]] = {}
        for book in books:
            if book.shelf_id is None:
                continue
            books_by_shelf.setdefault(book.shelf_id, []).append(
                ExportBookItem(book=book, record=record_map.get(book.bibliographic_record_id))
            )

        mapped_sections: list[MapSectionData] = []
        for section in sections:
            mapped_sections.append(
                MapSectionData(
                    section=section,
                    shelves=[
                        MapShelfBooks(shelf=shelf, books=books_by_shelf.get(shelf.id, []))
                        for shelf in shelves_by_section.get(section.id, [])
                    ],
                )
            )
        return bookcase, mapped_sections


async def _get_room_for_family(room_repo: RoomRepository, room_id: UUID, family_id: UUID) -> Room:
    room = await room_repo.find_by_id(room_id)
    if room is None:
        raise LookupError("Room not found")
    if room.family_id != family_id:
        raise PermissionError("Access denied")
    return room


async def _get_bookcase_for_family(bookcase_repo: BookcaseRepository, bookcase_id: UUID, family_id: UUID) -> Bookcase:
    bookcase = await bookcase_repo.find_by_id(bookcase_id)
    if bookcase is None:
        raise LookupError("Bookcase not found")
    if bookcase.family_id != family_id:
        raise PermissionError("Access denied")
    return bookcase


async def _get_section_for_family(
    section_repo: SectionRepository,
    bookcase_repo: BookcaseRepository,
    section_id: UUID,
    family_id: UUID,
) -> Section:
    section = await section_repo.find_by_id(section_id)
    if section is None:
        raise LookupError("Section not found")
    await _get_bookcase_for_family(bookcase_repo, section.bookcase_id, family_id)
    return section


async def _get_shelf_for_family(
    shelf_repo: ShelfRepository,
    section_repo: SectionRepository,
    bookcase_repo: BookcaseRepository,
    shelf_id: UUID,
    family_id: UUID,
) -> Shelf:
    shelf = await shelf_repo.find_by_id(shelf_id)
    if shelf is None:
        raise LookupError("Shelf not found")
    await _get_section_for_family(section_repo, bookcase_repo, shelf.section_id, family_id)
    return shelf


async def _get_record_for_family(
    record_repo: BibliographicRecordRepository,
    record_id: UUID,
    family_id: UUID,
) -> BibliographicRecord:
    record = await record_repo.find_by_id(record_id)
    if record is None:
        raise LookupError("Bibliographic record not found")
    if record.family_id != family_id:
        raise PermissionError("Access denied")
    return record


def _extract_year(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    for part in value.split("-"):
        if part[:4].isdigit():
            return int(part[:4])
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) >= 4:
        return int(digits[:4])
    return None
