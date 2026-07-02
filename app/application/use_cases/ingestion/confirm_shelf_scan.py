import logging
from dataclasses import dataclass
from uuid import UUID

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
class ConfirmShelfScanOutput:
	created_book_ids: list[UUID]
	skipped_titles: list[str]


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
		skipped: list[str] = []
		# Honour the spine order left-to-right regardless of the order the client
		# happened to send (e.g. after the user reordered or deselected some).
		for item in sorted(inp.items, key=lambda it: it.position):
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
				skipped.append(item.title)
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
		return ConfirmShelfScanOutput(created_book_ids=created, skipped_titles=skipped)
