import logging
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

import httpx
from rapidfuzz import fuzz

from app.application.services import normalize_isbn
from app.config import settings
from app.domain.entities import (
	BibliographicRecord,
	BookCondition,
	BookEventType,
	BookHistory,
	BookSource,
	OwnedBook,
	ReadingStatus,
)
from app.domain.repositories import (
	BibliographicRecordRepository,
	BookHistoryRepository,
	BookReadRepository,
	DuplicateCandidate,
	DuplicateJudge,
	IsbnLookupCacheRepository,
	OwnedBookRepository,
)
from app.utils import utcnow

logger = logging.getLogger(__name__)

# Page size for the fuzzy-dedup candidate scan — not a hard cap: _all_family_records
# loops find_all_by_family until a short page, so every record is covered
# regardless of family size, this only bounds round-trips per page.
_FUZZY_SCAN_PAGE_SIZE = 200


def _normalize_for_fuzzy_match(text: str) -> str:
	"""Lowercase, punctuation stripped, whitespace collapsed — so "The Name of
	the Rose!" and "the name of the rose" score as identical rather than
	merely similar."""
	return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text.lower())).strip()


@dataclass
class DuplicateBookConflict:
	conflict_type: Literal["isbn_match", "title_author_match", "fuzzy_match"]
	existing_book_id: UUID
	existing_record_id: UUID
	title: str
	main_author: str | None
	isbn: str | None
	# Who already has it and where — the check is family-wide, not owner-scoped
	# (two members can each legitimately own a copy), so the caller needs this
	# to decide whether adding a separate copy makes sense.
	existing_owner_id: UUID | None
	existing_room_id: UUID | None
	existing_bookcase_id: UUID | None
	existing_section_id: UUID | None
	existing_shelf_id: UUID | None
	# Only set for conflict_type="fuzzy_match" when the ambiguous-band LLM
	# judge ran — None for isbn_match/title_author_match (no judgement needed)
	# and for a fuzzy_match confident enough to skip the LLM call entirely.
	match_reason: str | None = None


class DuplicateBookError(Exception):
	"""Raised instead of creating the book when it looks like the caller
	already owns this exact book and hasn't confirmed they want a second copy
	anyway (see AddBookInput.is_intentional_duplicate)."""

	def __init__(self, conflict: DuplicateBookConflict) -> None:
		self.conflict = conflict
		super().__init__(f"Duplicate book detected: {conflict.conflict_type}")


@dataclass
class AddBookInput:
	family_id: UUID
	changed_by: UUID
	bibliographic_record_id: UUID | None = None
	title: str | None = None
	main_author: str | None = None
	other_authors: list[str] | None = None
	isbn: str | None = None
	publisher: str | None = None
	publication_year: int | None = None
	language: str | None = None
	genre: str | None = None
	cover_url: str | None = None
	record_notes: str | None = None
	notes: str | None = None
	room_id: UUID | None = None
	bookcase_id: UUID | None = None
	section_id: UUID | None = None
	shelf_id: UUID | None = None
	shelf_position: int | None = None
	position_description: str | None = None
	condition: BookCondition | None = None
	purchase_date: date | None = None
	purchase_price: Decimal | None = None
	source: BookSource | None = None
	reading_status: ReadingStatus = ReadingStatus.TO_READ
	owner_id: UUID | None = None
	tags: list[str] | None = None
	is_intentional_duplicate: bool = False
	duplicate_notes: str | None = None


class AddBookUseCase:
	def __init__(
		self,
		record_repo: BibliographicRecordRepository,
		book_repo: OwnedBookRepository,
		history_repo: BookHistoryRepository,
		cache_repo: IsbnLookupCacheRepository,
		read_repo: BookReadRepository,
		http_client: httpx.AsyncClient | None = None,
		dedup_judge: DuplicateJudge | None = None,
	) -> None:
		self._record_repo = record_repo
		self._book_repo = book_repo
		self._history_repo = history_repo
		self._cache_repo = cache_repo
		self._read_repo = read_repo
		self._http_client = http_client
		self._dedup_judge = dedup_judge

	async def execute(self, inp: AddBookInput) -> OwnedBook:
		record = await self._resolve_bibliographic_record(inp)

		if not inp.is_intentional_duplicate:
			conflict = await self._check_for_duplicate(inp, record)
			if conflict:
				raise DuplicateBookError(conflict)

		# "Read" is per-member (see BookRead), so the stored column never holds
		# it — only "reading" (claims the shared copy) or "to_read".
		initial_status = ReadingStatus.READING if inp.reading_status == ReadingStatus.READING else ReadingStatus.TO_READ
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
				reading_status=initial_status,
				current_reader_id=inp.changed_by if inp.reading_status == ReadingStatus.READING else None,
				owner_id=inp.owner_id,
				tags=inp.tags or [],
				notes=inp.notes,
				is_intentional_duplicate=inp.is_intentional_duplicate,
				duplicate_notes=inp.duplicate_notes,
				created_at=utcnow(),
				updated_at=utcnow(),
			)
		)
		if inp.reading_status == ReadingStatus.READ:
			await self._read_repo.add(book.id, inp.changed_by)
		book.reading_status = book.reading_status_for(
			inp.changed_by, inp.reading_status == ReadingStatus.READ
		)
		await self._history_repo.save(
			BookHistory(
				owned_book_id=book.id,
				event_type=BookEventType.CREATED,
				changed_by=inp.changed_by,
				new_data={"reading_status": book.reading_status, "shelf_id": str(book.shelf_id) if book.shelf_id else None},
				created_at=utcnow(),
			)
		)
		return book

	async def _check_for_duplicate(self, inp: AddBookInput, record: BibliographicRecord) -> DuplicateBookConflict | None:
		"""Two ways a new book can look like one the family already has — this
		is a family-wide check, not scoped to an owner: two different members
		can legitimately each own a copy, so this never blocks that, it just
		surfaces who already has it (and where) so the caller can decide.
		  1. Same resolved record (i.e. same ISBN) — find_by_isbn already
		     reused the existing record, so this is the simple case.
		  2. A *different* record with the same title/author — catches the
		     case where the same book was added twice under different (or
		     missing) ISBNs and so got two separate records.
		"""
		existing = await self._book_repo.find_one_by_record(record.id)
		if existing:
			return self._to_conflict("isbn_match", existing, record)

		candidate = await self._record_repo.find_by_title_author(inp.family_id, record.title, record.main_author)
		if candidate and candidate.id != record.id:
			existing = await self._book_repo.find_one_by_record(candidate.id)
			if existing:
				return self._to_conflict("title_author_match", existing, candidate)

		return await self._check_for_fuzzy_duplicate(inp, record)

	async def _check_for_fuzzy_duplicate(
		self, inp: AddBookInput, record: BibliographicRecord
	) -> DuplicateBookConflict | None:
		"""Third level, only reached when neither exact check matched: catches
		different editions/printings, translated titles, or typos that an exact
		string comparison can't. Most adds never reach the network call below —
		only candidates inside the ambiguous similarity band do."""
		if self._dedup_judge is None:
			return None

		others = [r for r in await self._all_family_records(inp.family_id) if r.id != record.id]
		if not others:
			return None

		# Two different scores, deliberately:
		#  - loose_score (token_set_ratio) finds CANDIDATES worth looking at —
		#    it scores a title that's a pure subtitle/edition-suffix superset of
		#    another ("Dune" vs "Dune — 40th Anniversary Edition") as a strong
		#    match, ignoring the extra tokens. That's correct for "is this worth
		#    asking about" but too lenient to auto-confirm a duplicate on its
		#    own: it would also score "Dune" highly against any unrelated title
		#    that happens to contain the word "dune".
		#  - strict_score (token_sort_ratio) is what gates skipping the LLM
		#    entirely — it only scores high when the two titles are near
		#    word-for-word identical (mod case/punctuation/order), so an
		#    edition-suffix pair like the one above correctly falls through to
		#    the LLM judgement instead of auto-confirming.
		best_record: BibliographicRecord | None = None
		best_loose_score = 0.0
		best_strict_score = 0.0
		normalized_title = _normalize_for_fuzzy_match(record.title)
		normalized_author = _normalize_for_fuzzy_match(record.main_author) if record.main_author else None
		for other in others:
			other_title = _normalize_for_fuzzy_match(other.title)
			loose_title_score = fuzz.token_set_ratio(normalized_title, other_title) / 100
			strict_title_score = fuzz.token_sort_ratio(normalized_title, other_title) / 100
			if normalized_author and other.main_author:
				other_author = _normalize_for_fuzzy_match(other.main_author)
				author_score = fuzz.token_sort_ratio(normalized_author, other_author) / 100
				loose_score = 0.7 * loose_title_score + 0.3 * author_score
				strict_score = 0.7 * strict_title_score + 0.3 * author_score
			else:
				loose_score = loose_title_score
				strict_score = strict_title_score
			if loose_score > best_loose_score:
				best_loose_score = loose_score
				best_strict_score = strict_score
				best_record = other

		if best_record is None or best_loose_score < settings.fuzzy_dedup_low_threshold:
			return None

		existing = await self._book_repo.find_one_by_record(best_record.id)
		if not existing:
			return None

		if best_strict_score >= settings.fuzzy_dedup_high_threshold:
			return self._to_conflict("fuzzy_match", existing, best_record)

		judgement = await self._dedup_judge.judge(
			DuplicateCandidate(
				title=record.title, main_author=record.main_author, publication_year=record.publication_year
			),
			DuplicateCandidate(
				title=best_record.title,
				main_author=best_record.main_author,
				publication_year=best_record.publication_year,
			),
		)
		if not judgement.is_duplicate:
			return None
		return self._to_conflict("fuzzy_match", existing, best_record, match_reason=judgement.reason)

	async def _all_family_records(self, family_id: UUID) -> list[BibliographicRecord]:
		"""Every record for the family, regardless of how many — find_all_by_family
		is paginated for the catalog list UI, but a fuzzy duplicate scan that
		silently only checked the first page would miss real duplicates in any
		library bigger than one page."""
		records: list[BibliographicRecord] = []
		offset = 0
		while True:
			page = await self._record_repo.find_all_by_family(family_id, limit=_FUZZY_SCAN_PAGE_SIZE, offset=offset)
			records.extend(page)
			if len(page) < _FUZZY_SCAN_PAGE_SIZE:
				return records
			offset += _FUZZY_SCAN_PAGE_SIZE

	@staticmethod
	def _to_conflict(
		conflict_type: Literal["isbn_match", "title_author_match", "fuzzy_match"],
		existing: OwnedBook,
		record: BibliographicRecord,
		match_reason: str | None = None,
	) -> DuplicateBookConflict:
		return DuplicateBookConflict(
			conflict_type=conflict_type,
			existing_book_id=existing.id,
			existing_record_id=record.id,
			title=record.title,
			main_author=record.main_author,
			isbn=record.isbn,
			existing_owner_id=existing.owner_id,
			existing_room_id=existing.room_id,
			existing_bookcase_id=existing.bookcase_id,
			existing_section_id=existing.section_id,
			existing_shelf_id=existing.shelf_id,
			match_reason=match_reason,
		)

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
