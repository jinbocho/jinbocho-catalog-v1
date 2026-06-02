from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4


@dataclass
class BookHistory:
	owned_book_id: UUID
	event_type: str
	changed_by: UUID
	old_data: dict[str, Any] | None = None
	new_data: dict[str, Any] | None = None
	id: UUID = field(default_factory=uuid4)
	created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
