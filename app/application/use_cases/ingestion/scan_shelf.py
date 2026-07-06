import asyncio
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

from rapidfuzz import fuzz

from app.domain.repositories import (
	BibliographicRecordRepository,
	BookcaseRepository,
	BookSearchProvider,
	OwnedBookRepository,
	SectionRepository,
	ShelfRepository,
)
from app.domain.repositories.shelf_spine_reader import ShelfSpineReader, SpineReading

# A provider hit is trusted (pre-selected in the FE review screen) only when its
# title/author are near word-for-word the spine transcription; between the two
# thresholds the hit is still shown but flagged for the user to double-check.
_MATCHED_THRESHOLD = 0.85
_UNCERTAIN_THRESHOLD = 0.50
_PROVIDER_MAX_RESULTS = 3

ShelfScanMatchStatus = Literal["matched", "uncertain", "not_found"]


@dataclass
class ScanShelfInput:
	library_id: UUID
	shelf_id: UUID
	image_base64: str
	media_type: str


@dataclass
class ShelfScanCandidate:
	spine_title: str
	spine_author: str | None
	position: int
	status: ShelfScanMatchStatus
	already_owned: bool
	metadata: dict[str, Any] | None


@dataclass
class ScanShelfOutput:
	available: bool
	candidates: list[ShelfScanCandidate]
	reason: str = "ok"  # mirrors the AI service SpineReadStatus when unavailable


class ScanShelfUseCase:
	def __init__(
		self,
		shelf_repo: ShelfRepository,
		section_repo: SectionRepository,
		bookcase_repo: BookcaseRepository,
		spine_reader: ShelfSpineReader,
		search_provider: BookSearchProvider,
		record_repo: BibliographicRecordRepository,
		book_repo: OwnedBookRepository,
	) -> None:
		self._shelf_repo = shelf_repo
		self._section_repo = section_repo
		self._bookcase_repo = bookcase_repo
		self._spine_reader = spine_reader
		self._search_provider = search_provider
		self._record_repo = record_repo
		self._book_repo = book_repo

	async def execute(self, inp: ScanShelfInput) -> ScanShelfOutput:
		await validate_shelf_ownership(
			inp.library_id, inp.shelf_id, self._shelf_repo, self._section_repo, self._bookcase_repo
		)

		read = await self._spine_reader.read_spines(inp.image_base64, inp.media_type)
		if not read.available:
			return ScanShelfOutput(available=False, candidates=[], reason=read.reason)

		# Provider lookups run concurrently: a full shelf is ~25 spines and the
		# whole scan must stay well inside the gateway's 30s upstream timeout.
		candidates = list(
			await asyncio.gather(*(self._match_spine(inp.library_id, spine) for spine in read.spines))
		)
		return ScanShelfOutput(available=True, candidates=candidates)

	async def _match_spine(self, library_id: UUID, spine: SpineReading) -> ShelfScanCandidate:
		results = await self._search_provider.search(spine.title, spine.author, _PROVIDER_MAX_RESULTS)

		best: dict[str, Any] | None = None
		best_score = 0.0
		for result in results:
			score = _similarity(spine, result)
			if score > best_score:
				best_score = score
				best = result

		status: ShelfScanMatchStatus
		if best is not None and best_score >= _MATCHED_THRESHOLD:
			status = "matched"
		elif best is not None and best_score >= _UNCERTAIN_THRESHOLD:
			status = "uncertain"
		else:
			status = "not_found"
			best = None

		title = str(best["title"]) if best else spine.title
		author = best.get("main_author") if best else spine.author
		return ShelfScanCandidate(
			spine_title=spine.title,
			spine_author=spine.author,
			position=spine.position,
			status=status,
			already_owned=await self._is_already_owned(library_id, title, author),
			metadata=best,
		)

	async def _is_already_owned(self, library_id: UUID, title: str, author: str | None) -> bool:
		record = await self._record_repo.find_by_title_author(library_id, title, author)
		if record is None:
			return False
		return await self._book_repo.exists_by_bibliographic_record_id(record.id)


async def validate_shelf_ownership(
	library_id: UUID,
	shelf_id: UUID,
	shelf_repo: ShelfRepository,
	section_repo: SectionRepository,
	bookcase_repo: BookcaseRepository,
) -> "ResolvedShelfLocation":
	"""Walks shelf -> section -> bookcase to prove the shelf belongs to the
	library, and returns the full location chain needed to position a book."""
	shelf = await shelf_repo.find_by_id(shelf_id)
	if shelf is None:
		raise LookupError(f"Shelf {shelf_id} not found")
	section = await section_repo.find_by_id(shelf.section_id)
	if section is None:
		raise LookupError(f"Section {shelf.section_id} not found")
	bookcase = await bookcase_repo.find_by_id(section.bookcase_id)
	if bookcase is None:
		raise LookupError(f"Bookcase {section.bookcase_id} not found")
	if bookcase.library_id != library_id:
		raise PermissionError("Shelf belongs to a different library")
	return ResolvedShelfLocation(
		room_id=bookcase.room_id,
		bookcase_id=bookcase.id,
		section_id=section.id,
		shelf_id=shelf.id,
	)


@dataclass
class ResolvedShelfLocation:
	room_id: UUID
	bookcase_id: UUID
	section_id: UUID
	shelf_id: UUID


def _similarity(spine: SpineReading, result: dict[str, Any]) -> float:
	result_title = result.get("title")
	if not isinstance(result_title, str) or not result_title:
		return 0.0
	title_score = fuzz.token_sort_ratio(spine.title.lower(), result_title.lower()) / 100
	result_author = result.get("main_author")
	if spine.author and isinstance(result_author, str) and result_author:
		author_score = fuzz.token_sort_ratio(spine.author.lower(), result_author.lower()) / 100
		return 0.7 * title_score + 0.3 * author_score
	return title_score
