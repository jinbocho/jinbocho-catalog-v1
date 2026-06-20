from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.domain.entities import (
	BibliographicRecord,
	BookHistory,
	BookLoan,
	BookRead,
	Bookcase,
	OwnedBook,
	Room,
	Section,
	Shelf,
)
from app.domain.repositories import (
	BibliographicRecordRepository,
	BookHistoryRepository,
	BookLoanRepository,
	BookReadRepository,
	BookcaseRepository,
	OwnedBookRepository,
	RoomRepository,
	SectionRepository,
	ShelfRepository,
)
from app.utils import utcnow

# --- Input items -------------------------------------------------------------
# Deliberately separate from the domain entities (which require family_id /
# server-assigned defaults that don't make sense for an as-exported payload)
# and from the API schemas (the application layer must not depend on them).


@dataclass
class ImportRoomItem:
	id: UUID
	name: str
	description: str | None = None
	created_at: datetime | None = None
	updated_at: datetime | None = None


@dataclass
class ImportBookcaseItem:
	id: UUID
	room_id: UUID
	name: str
	description: str | None = None
	type: str | None = None
	notes: str | None = None
	image_url: str | None = None
	created_at: datetime | None = None
	updated_at: datetime | None = None


@dataclass
class ImportSectionItem:
	id: UUID
	bookcase_id: UUID
	section_index: int
	label: str | None = None
	created_at: datetime | None = None
	updated_at: datetime | None = None


@dataclass
class ImportShelfItem:
	id: UUID
	section_id: UUID
	shelf_index: int
	notes: str | None = None
	created_at: datetime | None = None
	updated_at: datetime | None = None


@dataclass
class ImportRecordItem:
	id: UUID
	title: str
	main_author: str | None = None
	other_authors: list[str] = field(default_factory=list)
	isbn: str | None = None
	publisher: str | None = None
	publication_year: int | None = None
	language: str | None = None
	genre: str | None = None
	genre_raw: str | None = None
	cover_url: str | None = None
	notes: str | None = None
	incipit: str | None = None
	incipit_source: str | None = None
	incipit_generated_at: datetime | None = None
	created_at: datetime | None = None
	updated_at: datetime | None = None


@dataclass
class ImportOwnedBookItem:
	id: UUID
	bibliographic_record_id: UUID
	room_id: UUID | None = None
	bookcase_id: UUID | None = None
	section_id: UUID | None = None
	shelf_id: UUID | None = None
	shelf_position: int | None = None
	position_description: str | None = None
	condition: str | None = None
	purchase_date: date | None = None
	purchase_price: Decimal | None = None
	source: str | None = None
	reading_status: str = "to_read"
	current_reader_id: UUID | None = None
	owner_id: UUID | None = None
	tags: list[str] = field(default_factory=list)
	notes: str | None = None
	is_intentional_duplicate: bool = False
	duplicate_notes: str | None = None
	created_at: datetime | None = None
	updated_at: datetime | None = None


@dataclass
class ImportBookReadItem:
	id: UUID
	owned_book_id: UUID
	user_id: UUID
	read_at: datetime


@dataclass
class ImportBookLoanItem:
	id: UUID
	owned_book_id: UUID
	borrower_name: str
	loaned_at: datetime
	due_date: datetime | None = None
	returned_at: datetime | None = None


@dataclass
class ImportBookHistoryItem:
	id: UUID
	owned_book_id: UUID
	event_type: str
	changed_by: UUID
	old_data: dict[str, Any] | None = None
	new_data: dict[str, Any] | None = None
	created_at: datetime | None = None


@dataclass
class ImportFullLibraryInput:
	family_id: UUID
	user_id_map: dict[UUID, UUID] = field(default_factory=dict)
	rooms: list[ImportRoomItem] = field(default_factory=list)
	bookcases: list[ImportBookcaseItem] = field(default_factory=list)
	sections: list[ImportSectionItem] = field(default_factory=list)
	shelves: list[ImportShelfItem] = field(default_factory=list)
	bibliographic_records: list[ImportRecordItem] = field(default_factory=list)
	owned_books: list[ImportOwnedBookItem] = field(default_factory=list)
	book_reads: list[ImportBookReadItem] = field(default_factory=list)
	book_loans: list[ImportBookLoanItem] = field(default_factory=list)
	book_history: list[ImportBookHistoryItem] = field(default_factory=list)


@dataclass
class ImportFullLibraryOutput:
	rooms_imported: int = 0
	rooms_deduped: int = 0
	bookcases_imported: int = 0
	bookcases_deduped: int = 0
	sections_imported: int = 0
	sections_deduped: int = 0
	shelves_imported: int = 0
	shelves_deduped: int = 0
	records_imported: int = 0
	records_deduped: int = 0
	owned_books_imported: int = 0
	owned_books_deduped: int = 0
	book_reads_imported: int = 0
	book_loans_imported: int = 0
	book_history_imported: int = 0


class ImportFullLibraryUseCase:
	"""Restores a full library backup into the caller's family.

	Every entity gets a brand-new id on import (never the one from the
	export) and an old-id -> new-id map is built as it goes, used to rewrite
	every reference (bookcase.room_id, owned_book.bibliographic_record_id,
	book_read.owned_book_id, ...). This is deliberate, not incidental:
	preserving the original id and upserting by it is only safe if the
	target database is guaranteed to never already contain that id under a
	*different* family — which merging into an existing, non-empty family
	cannot guarantee (the id could belong to the very family the backup was
	exported from, still live in the same database). Reusing an existing id
	would silently land the import on that unrelated row instead of creating
	a new one. Random ids make that collision practically impossible.

	Every entity is deduplicated against what the family already has before
	being inserted, by a natural key rather than the (regenerated) id — so
	re-importing the same backup, or merging two overlapping libraries, does
	not pile up duplicates:
	  - bibliographic records: (family_id, isbn), or (family_id, title,
	    main_author) when isbn is absent — the DB enforces the isbn case as a
	    real uniqueness constraint, so this also avoids a hard failure on merge.
	  - rooms: (family_id, name). bookcases: (room_id, name).
	  - sections: (bookcase_id, section_index). shelves: (section_id,
	    shelf_index) — both already DB-unique, so this also avoids a hard
	    failure on merge.
	  - owned books: (record, room, bookcase, section, shelf, shelf_position)
	    — the same record in the exact same physical slot is treated as the
	    same copy; the same record with a different (or no) location is a
	    genuinely separate physical copy and is kept (the domain already
	    models multiple copies via is_intentional_duplicate).
	  - reads: (owned_book, user) — already DB-unique. loans: (owned_book,
	    borrower_name, loaned_at). history: (owned_book, event_type,
	    changed_by, created_at).
	In every dedup case the *existing* row wins; the imported one is discarded
	except for the id remap, so re-running an import never overwrites data
	already in the family.

	Cross-service user ids (owner_id, current_reader_id, book_reads.user_id,
	book_history.changed_by) are rewritten through `user_id_map`, built by the
	auth-service's POST /v1/users/import that must run first; an id with no
	entry in the map is dropped (set to null) rather than left dangling.
	"""

	def __init__(
		self,
		room_repo: RoomRepository,
		bookcase_repo: BookcaseRepository,
		section_repo: SectionRepository,
		shelf_repo: ShelfRepository,
		record_repo: BibliographicRecordRepository,
		book_repo: OwnedBookRepository,
		book_read_repo: BookReadRepository,
		book_loan_repo: BookLoanRepository,
		book_history_repo: BookHistoryRepository,
	) -> None:
		self._room_repo = room_repo
		self._bookcase_repo = bookcase_repo
		self._section_repo = section_repo
		self._shelf_repo = shelf_repo
		self._record_repo = record_repo
		self._book_repo = book_repo
		self._book_read_repo = book_read_repo
		self._book_loan_repo = book_loan_repo
		self._book_history_repo = book_history_repo

	async def execute(self, input: ImportFullLibraryInput) -> ImportFullLibraryOutput:
		self._validate_referential_integrity(input)
		out = ImportFullLibraryOutput()
		now = utcnow()

		record_id_map: dict[UUID, UUID] = {}
		for record_item in input.bibliographic_records:
			existing = (
				await self._record_repo.find_by_isbn(input.family_id, record_item.isbn)
				if record_item.isbn
				else await self._record_repo.find_by_title_author(input.family_id, record_item.title, record_item.main_author)
			)
			if existing:
				record_id_map[record_item.id] = existing.id
				out.records_deduped += 1
				continue
			new_id = uuid4()
			await self._record_repo.save(
				BibliographicRecord(
					id=new_id,
					family_id=input.family_id,
					title=record_item.title,
					main_author=record_item.main_author,
					other_authors=record_item.other_authors,
					isbn=record_item.isbn,
					publisher=record_item.publisher,
					publication_year=record_item.publication_year,
					language=record_item.language,
					genre=record_item.genre,
					genre_raw=record_item.genre_raw,
					cover_url=record_item.cover_url,
					notes=record_item.notes,
					incipit=record_item.incipit,
					incipit_source=record_item.incipit_source,
					incipit_generated_at=record_item.incipit_generated_at,
					created_at=record_item.created_at or now,
					updated_at=record_item.updated_at or now,
				)
			)
			record_id_map[record_item.id] = new_id
			out.records_imported += 1

		room_id_map: dict[UUID, UUID] = {}
		for room_item in input.rooms:
			existing_room = await self._room_repo.find_by_name(input.family_id, room_item.name)
			if existing_room:
				room_id_map[room_item.id] = existing_room.id
				out.rooms_deduped += 1
				continue
			new_id = uuid4()
			await self._room_repo.save(
				Room(
					id=new_id,
					family_id=input.family_id,
					name=room_item.name,
					description=room_item.description,
					created_at=room_item.created_at or now,
					updated_at=room_item.updated_at or now,
				)
			)
			room_id_map[room_item.id] = new_id
			out.rooms_imported += 1

		bookcase_id_map: dict[UUID, UUID] = {}
		for bookcase_item in input.bookcases:
			resolved_room_id = room_id_map[bookcase_item.room_id]
			existing_bookcase = await self._bookcase_repo.find_by_name(resolved_room_id, bookcase_item.name)
			if existing_bookcase:
				bookcase_id_map[bookcase_item.id] = existing_bookcase.id
				out.bookcases_deduped += 1
				continue
			new_id = uuid4()
			await self._bookcase_repo.save(
				Bookcase(
					id=new_id,
					family_id=input.family_id,
					room_id=resolved_room_id,
					name=bookcase_item.name,
					description=bookcase_item.description,
					type=bookcase_item.type,
					notes=bookcase_item.notes,
					image_url=bookcase_item.image_url,
					created_at=bookcase_item.created_at or now,
					updated_at=bookcase_item.updated_at or now,
				)
			)
			bookcase_id_map[bookcase_item.id] = new_id
			out.bookcases_imported += 1

		section_id_map: dict[UUID, UUID] = {}
		for section_item in input.sections:
			resolved_bookcase_id = bookcase_id_map[section_item.bookcase_id]
			existing_section = await self._section_repo.find_by_index(resolved_bookcase_id, section_item.section_index)
			if existing_section:
				section_id_map[section_item.id] = existing_section.id
				out.sections_deduped += 1
				continue
			new_id = uuid4()
			await self._section_repo.save(
				Section(
					id=new_id,
					bookcase_id=resolved_bookcase_id,
					section_index=section_item.section_index,
					label=section_item.label,
					created_at=section_item.created_at or now,
					updated_at=section_item.updated_at or now,
				)
			)
			section_id_map[section_item.id] = new_id
			out.sections_imported += 1

		shelf_id_map: dict[UUID, UUID] = {}
		for shelf_item in input.shelves:
			resolved_section_id = section_id_map[shelf_item.section_id]
			existing_shelf = await self._shelf_repo.find_by_index(resolved_section_id, shelf_item.shelf_index)
			if existing_shelf:
				shelf_id_map[shelf_item.id] = existing_shelf.id
				out.shelves_deduped += 1
				continue
			new_id = uuid4()
			await self._shelf_repo.save(
				Shelf(
					id=new_id,
					section_id=resolved_section_id,
					shelf_index=shelf_item.shelf_index,
					notes=shelf_item.notes,
					created_at=shelf_item.created_at or now,
					updated_at=shelf_item.updated_at or now,
				)
			)
			shelf_id_map[shelf_item.id] = new_id
			out.shelves_imported += 1

		book_id_map: dict[UUID, UUID] = {}
		for book_item in input.owned_books:
			book_record_id = record_id_map[book_item.bibliographic_record_id]
			book_room_id = room_id_map.get(book_item.room_id) if book_item.room_id else None
			book_bookcase_id = bookcase_id_map.get(book_item.bookcase_id) if book_item.bookcase_id else None
			book_section_id = section_id_map.get(book_item.section_id) if book_item.section_id else None
			book_shelf_id = shelf_id_map.get(book_item.shelf_id) if book_item.shelf_id else None

			existing_book = await self._book_repo.find_duplicate(
				family_id=input.family_id,
				bibliographic_record_id=book_record_id,
				room_id=book_room_id,
				bookcase_id=book_bookcase_id,
				section_id=book_section_id,
				shelf_id=book_shelf_id,
				shelf_position=book_item.shelf_position,
			)
			if existing_book:
				book_id_map[book_item.id] = existing_book.id
				out.owned_books_deduped += 1
				continue

			new_id = uuid4()
			await self._book_repo.save(
				OwnedBook(
					id=new_id,
					family_id=input.family_id,
					bibliographic_record_id=book_record_id,
					room_id=book_room_id,
					bookcase_id=book_bookcase_id,
					section_id=book_section_id,
					shelf_id=book_shelf_id,
					shelf_position=book_item.shelf_position,
					position_description=book_item.position_description,
					condition=book_item.condition,
					purchase_date=book_item.purchase_date,
					purchase_price=book_item.purchase_price,
					source=book_item.source,
					reading_status=book_item.reading_status,
					current_reader_id=input.user_id_map.get(book_item.current_reader_id) if book_item.current_reader_id else None,
					owner_id=input.user_id_map.get(book_item.owner_id) if book_item.owner_id else None,
					tags=book_item.tags,
					notes=book_item.notes,
					is_intentional_duplicate=book_item.is_intentional_duplicate,
					duplicate_notes=book_item.duplicate_notes,
					created_at=book_item.created_at or now,
					updated_at=book_item.updated_at or now,
				)
			)
			book_id_map[book_item.id] = new_id
			out.owned_books_imported += 1

		for read_item in input.book_reads:
			if read_item.owned_book_id not in book_id_map:
				continue
			await self._book_read_repo.restore(
				BookRead(
					id=uuid4(),
					owned_book_id=book_id_map[read_item.owned_book_id],
					user_id=input.user_id_map.get(read_item.user_id, read_item.user_id),
					read_at=read_item.read_at,
				)
			)
			out.book_reads_imported += 1

		for loan_item in input.book_loans:
			if loan_item.owned_book_id not in book_id_map:
				continue
			await self._book_loan_repo.restore(
				BookLoan(
					id=uuid4(),
					owned_book_id=book_id_map[loan_item.owned_book_id],
					borrower_name=loan_item.borrower_name,
					loaned_at=loan_item.loaned_at,
					due_date=loan_item.due_date,
					returned_at=loan_item.returned_at,
				)
			)
			out.book_loans_imported += 1

		for history_item in input.book_history:
			if history_item.owned_book_id not in book_id_map:
				continue
			await self._book_history_repo.restore(
				BookHistory(
					id=uuid4(),
					owned_book_id=book_id_map[history_item.owned_book_id],
					event_type=history_item.event_type,
					changed_by=input.user_id_map.get(history_item.changed_by, history_item.changed_by),
					old_data=history_item.old_data,
					new_data=history_item.new_data,
					created_at=history_item.created_at or now,
				)
			)
			out.book_history_imported += 1

		return out

	@staticmethod
	def _validate_referential_integrity(input: ImportFullLibraryInput) -> None:
		"""Rejects a structurally broken payload before writing anything."""
		room_ids = {r.id for r in input.rooms}
		bookcase_ids = {b.id for b in input.bookcases}
		section_ids = {s.id for s in input.sections}
		shelf_ids = {s.id for s in input.shelves}
		record_ids = {r.id for r in input.bibliographic_records}
		book_ids = {b.id for b in input.owned_books}

		for bc in input.bookcases:
			if bc.room_id not in room_ids:
				raise ValueError(f"Bookcase {bc.id} references room {bc.room_id}, not present in this export")
		for s in input.sections:
			if s.bookcase_id not in bookcase_ids:
				raise ValueError(f"Section {s.id} references bookcase {s.bookcase_id}, not present in this export")
		for sh in input.shelves:
			if sh.section_id not in section_ids:
				raise ValueError(f"Shelf {sh.id} references section {sh.section_id}, not present in this export")
		for b in input.owned_books:
			if b.bibliographic_record_id not in record_ids:
				raise ValueError(f"Owned book {b.id} references record {b.bibliographic_record_id}, not present in this export")
			for field_name, value, valid_ids in (
				("room_id", b.room_id, room_ids),
				("bookcase_id", b.bookcase_id, bookcase_ids),
				("section_id", b.section_id, section_ids),
				("shelf_id", b.shelf_id, shelf_ids),
			):
				if value is not None and value not in valid_ids:
					raise ValueError(f"Owned book {b.id} references {field_name} {value}, not present in this export")
		for r in input.book_reads:
			if r.owned_book_id not in book_ids:
				raise ValueError(f"Book read {r.id} references owned book {r.owned_book_id}, not present in this export")
		for loan in input.book_loans:
			if loan.owned_book_id not in book_ids:
				raise ValueError(f"Book loan {loan.id} references owned book {loan.owned_book_id}, not present in this export")
		for h in input.book_history:
			if h.owned_book_id not in book_ids:
				raise ValueError(f"Book history {h.id} references owned book {h.owned_book_id}, not present in this export")
