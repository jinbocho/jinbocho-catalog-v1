from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class BookEventType(StrEnum):
	CREATED = "created"
	METADATA_UPDATED = "metadata_updated"
	POSITION_CHANGED = "position_changed"
	READING_STATUS_CHANGED = "reading_status_changed"
	DELETED = "deleted"


@dataclass
class BookHistory:
	owned_book_id: UUID
	event_type: BookEventType
	changed_by: UUID
	old_data: dict[str, Any] | None = None
	new_data: dict[str, Any] | None = None
	id: UUID = field(default_factory=uuid4)
	created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
