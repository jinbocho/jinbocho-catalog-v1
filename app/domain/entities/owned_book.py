from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4


class ReadingStatus(str, Enum):
	TO_READ = "to_read"
	READING = "reading"
	READ = "read"


class BookCondition(str, Enum):
	NEW = "new"
	GOOD = "good"
	FAIR = "fair"
	POOR = "poor"


class BookSource(str, Enum):
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
	created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
	updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
