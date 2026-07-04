import logging
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from app.application.services import normalize_isbn
from app.application.use_cases.catalog.add_book import AddBookInput, AddBookUseCase
from app.application.use_cases.ingestion.scan_shelf import validate_shelf_ownership
from app.domain.errors import DuplicateBookError
from app.domain.repositories import (
	BookcaseRepository,
	OwnedBookRepository,
	SectionRepository,
	ShelfRepository,
)

logger = logging.getLogger(__name__)

ConfirmShelfScanSkipReason = Literal["already_owned", "duplicate_in_scan"]


@dataclass
class ConfirmShelfScanItem:
	title: str
	main_author: str | None = None
	isbn: str | None = None
	publisher: str | None = None
	publication_year: int | None = None
	language: str | None = None
	genre: str | None = None
	cover_url: str | None = None
	# Left-to-right order of the spine in the photo; determines shelf placement.
	position: int = 0
	is_intentional_duplicate: bool = False


@dataclass
class ConfirmShelfScanInput:
	family_id: UUID
	changed_by: UUID
	shelf_id: UUID
	items: list[ConfirmShelfScanItem]


@dataclass
class ConfirmShelfScanSkip:
	title: str
	reason: ConfirmShelfScanSkipReason
	# Echoes the spine's position so the caller can match a skip back to the
	# item it sent (title alone is ambiguous for a duplicate_in_scan pair).
	position: int


@dataclass
class ConfirmShelfScanOutput:
	created_book_ids: list[UUID]
	skipped: list[ConfirmShelfScanSkip]


class ConfirmShelfScanUseCase:
	"""Bulk-creates the books the user confirmed from a shelf scan preview,
	positioned progressively on the scanned shelf after any book already there.

	Delegates each creation to AddBookUseCase so record reuse (by ISBN),
	duplicate detection and history all behave exactly like a manual add; a
	duplicate skips that item instead of failing the whole batch, since the
	user has already reviewed the list."""

	def __init__(
		self,
		shelf_repo: ShelfRepository,
		section_repo: SectionRepository,
		bookcase_repo: BookcaseRepository,
		book_repo: OwnedBookRepository,
		add_book: AddBookUseCase,
	) -> None:
		self._shelf_repo = shelf_repo
		self._section_repo = section_repo
		self._bookcase_repo = bookcase_repo
		self._book_repo = book_repo
		self._add_book = add_book

	async def execute(self, inp: ConfirmShelfScanInput) -> ConfirmShelfScanOutput:
		location = await validate_shelf_ownership(
			inp.family_id, inp.shelf_id, self._shelf_repo, self._section_repo, self._bookcase_repo
		)

		existing = await self._book_repo.find_all_by_shelf_ids([inp.shelf_id])
		next_position = max((b.shelf_position or 0 for b in existing), default=0) + 1

		created: list[UUID] = []
		skipped: list[ConfirmShelfScanSkip] = []
		# Two spines in the same photo can resolve to the same book (e.g. two
		# copies standing side by side that neither one is owned yet, so the
		# per-item AddBookUseCase duplicate check wouldn't catch the first one
		# against the second). Catching that here — before it ever reaches
		# AddBookUseCase — means the second occurrence never attempts a write,
		# so it can never race a concurrent confirm on the same ISBN either.
		seen_keys: set[tuple[str, str]] = set()

		# Honour the spine order left-to-right regardless of the order the client
		# happened to send (e.g. after the user reordered or deselected some).
		for item in sorted(inp.items, key=lambda it: it.position):
			if not item.is_intentional_duplicate:
				key = _dedup_key(item)
				if key in seen_keys:
					skipped.append(ConfirmShelfScanSkip(item.title, "duplicate_in_scan", item.position))
					continue
				seen_keys.add(key)
			try:
				book = await self._add_book.execute(
					AddBookInput(
						family_id=inp.family_id,
						changed_by=inp.changed_by,
						title=item.title,
						main_author=item.main_author,
						isbn=item.isbn,
						publisher=item.publisher,
						publication_year=item.publication_year,
						language=item.language,
						genre=item.genre,
						cover_url=item.cover_url,
						room_id=location.room_id,
						bookcase_id=location.bookcase_id,
						section_id=location.section_id,
						shelf_id=location.shelf_id,
						shelf_position=next_position,
						is_intentional_duplicate=item.is_intentional_duplicate,
					)
				)
			except DuplicateBookError:
				skipped.append(ConfirmShelfScanSkip(item.title, "already_owned", item.position))
				continue
			created.append(book.id)
			next_position += 1

		logger.info(
			"Shelf scan confirmed for shelf %s in family %s: %d book(s) added, %d skipped",
			inp.shelf_id,
			inp.family_id,
			len(created),
			len(skipped),
		)
		return ConfirmShelfScanOutput(created_book_ids=created, skipped=skipped)


def _dedup_key(item: ConfirmShelfScanItem) -> tuple[str, str]:
	"""Identifies "the same book" across items of a single confirm batch: by
	ISBN when legible, otherwise by normalized title+author — good enough to
	catch the same spine matched twice without needing a provider round trip."""
	if item.isbn:
		return ("isbn", normalize_isbn(item.isbn))
	author = (item.main_author or "").strip().lower()
	return ("title", f"{item.title.strip().lower()}|{author}")
