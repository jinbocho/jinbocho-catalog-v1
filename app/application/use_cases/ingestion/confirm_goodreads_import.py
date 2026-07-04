import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.application.services import normalize_isbn
from app.application.use_cases.catalog.add_book import AddBookInput, AddBookUseCase
from app.domain.entities import BookRating, ReadingStatus
from app.domain.errors import DuplicateBookError
from app.domain.repositories import BookRatingRepository, BookReadRepository

logger = logging.getLogger(__name__)

ConfirmGoodreadsImportSkipReason = Literal["already_owned", "duplicate_in_import"]


@dataclass
class ConfirmGoodreadsImportItem:
	row_number: int
	title: str
	main_author: str | None = None
	other_authors: list[str] = field(default_factory=list)
	isbn: str | None = None
	publisher: str | None = None
	publication_year: int | None = None
	reading_status: ReadingStatus = ReadingStatus.TO_READ
	rating: int | None = None
	review: str | None = None
	read_at: datetime | None = None
	tags: list[str] = field(default_factory=list)
	is_intentional_duplicate: bool = False


@dataclass
class ConfirmGoodreadsImportInput:
	family_id: UUID
	changed_by: UUID
	items: list[ConfirmGoodreadsImportItem]


@dataclass
class ConfirmGoodreadsImportSkip:
	title: str
	reason: ConfirmGoodreadsImportSkipReason
	row_number: int


@dataclass
class ConfirmGoodreadsImportOutput:
	created_book_ids: list[UUID]
	skipped: list[ConfirmGoodreadsImportSkip]
	rated_count: int
	read_count: int


class ConfirmGoodreadsImportUseCase:
	"""Bulk-creates the books the user confirmed from a Goodreads CSV preview.

	Delegates each creation to AddBookUseCase so record reuse (by ISBN),
	duplicate detection and history all behave exactly like a manual add; a
	duplicate skips that item instead of failing the whole batch, since the
	user has already reviewed the list (same shape as ConfirmShelfScanUseCase).

	Books have no physical position — Goodreads has no location model — so
	room/bookcase/section/shelf are left unset; the user places them later.

	Rating and "read" are per-member, attached to changed_by (the family
	member running the import), and applied *after* AddBookUseCase creates the
	book — reading_status=READ is downgraded to TO_READ before it reaches
	AddBookInput so AddBookUseCase's own auto-mark-read (which always stamps
	"now") never fires; this use case adds the BookRead itself with the
	CSV's actual Date Read.
	"""

	def __init__(
		self,
		add_book: AddBookUseCase,
		read_repo: BookReadRepository,
		rating_repo: BookRatingRepository,
	) -> None:
		self._add_book = add_book
		self._read_repo = read_repo
		self._rating_repo = rating_repo

	async def execute(self, inp: ConfirmGoodreadsImportInput) -> ConfirmGoodreadsImportOutput:
		created: list[UUID] = []
		skipped: list[ConfirmGoodreadsImportSkip] = []
		rated_count = 0
		read_count = 0
		# Two CSV rows resolving to the same not-yet-owned book (duplicate
		# export entries) must not both be created — checked before the
		# per-item AddBookUseCase duplicate check, same as shelf scan.
		seen_keys: set[tuple[str, str]] = set()

		for item in inp.items:
			if not item.is_intentional_duplicate:
				key = _dedup_key(item)
				if key in seen_keys:
					skipped.append(ConfirmGoodreadsImportSkip(item.title, "duplicate_in_import", item.row_number))
					continue
				seen_keys.add(key)

			add_reading_status = (
				ReadingStatus.TO_READ if item.reading_status == ReadingStatus.READ else item.reading_status
			)
			try:
				book = await self._add_book.execute(
					AddBookInput(
						family_id=inp.family_id,
						changed_by=inp.changed_by,
						title=item.title,
						main_author=item.main_author,
						other_authors=item.other_authors,
						isbn=item.isbn,
						publisher=item.publisher,
						publication_year=item.publication_year,
						reading_status=add_reading_status,
						tags=item.tags,
						is_intentional_duplicate=item.is_intentional_duplicate,
					)
				)
			except DuplicateBookError:
				skipped.append(ConfirmGoodreadsImportSkip(item.title, "already_owned", item.row_number))
				continue

			if item.rating is not None:
				await self._rating_repo.add(
					BookRating(owned_book_id=book.id, user_id=inp.changed_by, rating=item.rating, review=item.review)
				)
				rated_count += 1
			if item.reading_status == ReadingStatus.READ:
				await self._read_repo.add(book.id, inp.changed_by, item.read_at)
				read_count += 1

			created.append(book.id)

		logger.info(
			"Goodreads import confirmed for family %s: %d book(s) added, %d skipped, %d rated, %d marked read",
			inp.family_id,
			len(created),
			len(skipped),
			rated_count,
			read_count,
		)
		return ConfirmGoodreadsImportOutput(
			created_book_ids=created, skipped=skipped, rated_count=rated_count, read_count=read_count
		)


def _dedup_key(item: ConfirmGoodreadsImportItem) -> tuple[str, str]:
	if item.isbn:
		return ("isbn", normalize_isbn(item.isbn))
	author = (item.main_author or "").strip().lower()
	return ("title", f"{item.title.strip().lower()}|{author}")
