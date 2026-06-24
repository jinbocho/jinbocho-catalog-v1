from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4


class ReadingStatus(StrEnum):
	TO_READ = "to_read"
	READING = "reading"
	READ = "read"


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
	family_id: UUID
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
	# Family member who owns this copy; all members can read it.
	# Users live in the auth service → bare UUID, no FK.
	owner_id: UUID | None = None
	tags: list[str] = field(default_factory=list)
	notes: str | None = None
	is_intentional_duplicate: bool = False
	duplicate_notes: str | None = None
	id: UUID = field(default_factory=uuid4)
	created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
	updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

	def reading_status_for(self, viewer_id: UUID, has_read: bool) -> ReadingStatus:
		"""Reading status as seen by a specific family member. "Reading" is
		inherently shared (only one person can hold the single physical copy
		at a time); "read" is per-member, derived from BookRead rows, so one
		member finishing the book doesn't mark it read for everyone else."""
		if self.current_reader_id == viewer_id:
			return ReadingStatus.READING
		if has_read:
			return ReadingStatus.READ
		return ReadingStatus.TO_READ
