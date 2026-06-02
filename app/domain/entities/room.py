from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class Room:
	family_id: UUID
	name: str
	description: str | None = None
	id: UUID = field(default_factory=uuid4)
	created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
	updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
