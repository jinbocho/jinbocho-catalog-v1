from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class Bookcase:
	family_id: UUID
	room_id: UUID
	name: str
	description: str | None = None
	type: str | None = None
	notes: str | None = None
	image_url: str | None = None
	id: UUID = field(default_factory=uuid4)
	created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
	updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
