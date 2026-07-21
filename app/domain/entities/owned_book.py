from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4


class ReadingStatus(StrEnum):
	TO_READ = "to_read"
	READING = "reading"
	READ = "read"
	# A reader chose to stop, recorded as a neutral fact — see KID-05 reader's
	# rights in jinbocho-docs/backlog/BACKLOG_KIDS_READING_EDUCATION.md.
	ABANDONED = "abandoned"


class BookCondition(StrEnum):
	NEW = "new"
	GOOD = "good"
	FAIR = "fair"
	POOR = "poor"


class BookSource(StrEnum):
	PURCHASED = "purchased"
	GIFT = "gift"
	BORROWED = "borrowed"
	OTHER = "other"


@dataclass
class OwnedBook:
	library_id: UUID
	bibliographic_record_id: UUID
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
	# Who is currently reading the (single physical) copy; None when nobody is.
	# Users live in the auth service → bare UUID, no FK.
	current_reader_id: UUID | None = None
	# Library member who owns this copy; all members can read it.
	# Users live in the auth service → bare UUID, no FK.
	owner_id: UUID | None = None
	tags: list[str] = field(default_factory=list)
	notes: str | None = None
	is_intentional_duplicate: bool = False
	duplicate_notes: str | None = None
	id: UUID = field(default_factory=uuid4)
	created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
	updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

	def reading_status_for(self, has_read: bool, has_abandoned: bool = False) -> ReadingStatus:
		"""Reading status as seen by a specific library member. "Reading" is
		inherently shared (only one person can hold the single physical copy
		at a time) — visible to every member regardless of who's holding it,
		not just the holder; "read" and "abandoned" are per-member, derived
		from BookRead/BookAbandonment rows, so one member's state never
		overrides what another member sees for the same copy."""
		if self.current_reader_id is not None:
			return ReadingStatus.READING
		if has_read:
			return ReadingStatus.READ
		if has_abandoned:
			return ReadingStatus.ABANDONED
		return ReadingStatus.TO_READ
