import asyncio
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

import httpx

from app.application.services import normalize_isbn
from app.config import settings
from app.domain.entities import BibliographicRecord, BookHistory, OwnedBook
from app.domain.repositories import (
	BibliographicRecordRepository,
	BookHistoryRepository,
	IsbnLookupCacheRepository,
	OwnedBookRepository,
)
from app.utils import utcnow

logger = logging.getLogger(__name__)


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
	owner_id: Optional[UUID] = None
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
		http_client: Optional[httpx.AsyncClient] = None,
	) -> None:
		self._record_repo = record_repo
		self._book_repo = book_repo
		self._history_repo = history_repo
		self._cache_repo = cache_repo
		self._http_client = http_client

	async def execute(self, inp: AddBookInput) -> OwnedBook:
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
				current_reader_id=inp.changed_by if inp.reading_status == "reading" else None,
				owner_id=inp.owner_id,
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
			normalized = normalize_isbn(inp.isbn)
			existing = await self._record_repo.find_by_isbn(inp.family_id, normalized)
			if existing:
				return existing

		metadata: dict[str, Any] = {
			"title": inp.title,
			"main_author": inp.main_author,
			"other_authors": inp.other_authors or [],
			"isbn": normalize_isbn(inp.isbn) if inp.isbn else None,
			"publisher": inp.publisher,
			"publication_year": inp.publication_year,
			"language": inp.language,
			"genre": inp.genre,
			"cover_url": inp.cover_url,
			"notes": inp.record_notes,
		}

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
