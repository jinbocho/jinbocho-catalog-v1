import re
from dataclasses import dataclass
from uuid import UUID

from rapidfuzz import fuzz

from app.application.use_cases.ingestion.scan_shelf import validate_shelf_ownership
from app.domain.repositories import (
	BibliographicRecordRepository,
	BookcaseRepository,
	OwnedBookRepository,
	SectionRepository,
	ShelfRepository,
)
from app.domain.repositories.shelf_spine_reader import ShelfSpineReader, SpineReading

# A spine and a shelved book are considered the same copy above this score.
_AUDIT_MATCH_THRESHOLD = 0.80


@dataclass
class AuditShelfInput:
	library_id: UUID
	shelf_id: UUID
	image_base64: str
	media_type: str


@dataclass
class AuditBook:
	owned_book_id: UUID
	title: str
	main_author: str | None


@dataclass
class AuditUnexpectedSpine:
	title: str
	author: str | None
	position: int


@dataclass
class AuditShelfOutput:
	available: bool
	# Books catalogued here AND seen in the photo.
	present: list[AuditBook]
	# Catalogued here but NOT seen in the photo — likely moved, lent, or lost.
	missing: list[AuditBook]
	# Seen in the photo but NOT catalogued here — likely misfiled or uncatalogued.
	unexpected: list[AuditUnexpectedSpine]
	reason: str = "ok"  # mirrors the AI service SpineReadStatus when unavailable


class AuditShelfUseCase:
	"""Reconciles a shelf's catalogued books against a fresh photo of it: which
	are still there, which have gone missing, and which are unexpectedly present.
	Reuses the same vision reader as the scan flow; matching is greedy so each
	shelved book is claimed by at most one spine (ADR-010, phase 3)."""

	def __init__(
		self,
		shelf_repo: ShelfRepository,
		section_repo: SectionRepository,
		bookcase_repo: BookcaseRepository,
		spine_reader: ShelfSpineReader,
		book_repo: OwnedBookRepository,
		record_repo: BibliographicRecordRepository,
	) -> None:
		self._shelf_repo = shelf_repo
		self._section_repo = section_repo
		self._bookcase_repo = bookcase_repo
		self._spine_reader = spine_reader
		self._book_repo = book_repo
		self._record_repo = record_repo

	async def execute(self, inp: AuditShelfInput) -> AuditShelfOutput:
		await validate_shelf_ownership(
			inp.library_id, inp.shelf_id, self._shelf_repo, self._section_repo, self._bookcase_repo
		)

		read = await self._spine_reader.read_spines(inp.image_base64, inp.media_type)
		if not read.available:
			return AuditShelfOutput(available=False, present=[], missing=[], unexpected=[], reason=read.reason)
		spines = read.spines

		books = await self._book_repo.find_all_by_shelf_ids([inp.shelf_id])
		records = await self._record_repo.find_all_by_ids([b.bibliographic_record_id for b in books])
		record_map = {r.id: r for r in records}

		shelved: list[AuditBook] = []
		for book in books:
			record = record_map.get(book.bibliographic_record_id)
			if record is None:
				continue
			shelved.append(AuditBook(owned_book_id=book.id, title=record.title, main_author=record.main_author))

		present: list[AuditBook] = []
		missing: list[AuditBook] = []
		unexpected: list[AuditUnexpectedSpine] = []
		claimed_spines: set[int] = set()

		for shelved_book in shelved:
			best_index = -1
			best_score = 0.0
			for index, spine in enumerate(spines):
				if index in claimed_spines:
					continue
				score = _match_score(spine, shelved_book.title, shelved_book.main_author)
				if score > best_score:
					best_score = score
					best_index = index
			if best_index >= 0 and best_score >= _AUDIT_MATCH_THRESHOLD:
				claimed_spines.add(best_index)
				present.append(shelved_book)
			else:
				missing.append(shelved_book)

		for index, spine in enumerate(spines):
			if index not in claimed_spines:
				unexpected.append(
					AuditUnexpectedSpine(title=spine.title, author=spine.author, position=spine.position)
				)

		return AuditShelfOutput(available=True, present=present, missing=missing, unexpected=unexpected)


def _normalize(text: str) -> str:
	return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text.lower())).strip()


def _match_score(spine: SpineReading, title: str, author: str | None) -> float:
	title_score = fuzz.token_sort_ratio(_normalize(spine.title), _normalize(title)) / 100
	if spine.author and author:
		author_score = fuzz.token_sort_ratio(_normalize(spine.author), _normalize(author)) / 100
		return 0.7 * title_score + 0.3 * author_score
	return title_score
