from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID


class LibraryRole(StrEnum):
	ADMIN = "admin"
	EDITOR = "editor"
	VIEWER = "viewer"


@dataclass
class RemovedMember:
	"""A snapshot of a library member's identity, captured at the moment
	they're removed from the library in auth-service. Catalog-service is the
	only place that still holds a dangling reference to them afterwards
	(owner_id, current_reader_id, ...) — once the auth-service row is
	hard-deleted, their name/email are gone for good unless preserved here,
	so a future export/import can recreate the real account instead of
	leaving the reference unowned or inventing a placeholder."""

	id: UUID  # the original auth-service user id — the join key from owner_id/etc.
	library_id: UUID
	full_name: str
	email: str
	role: LibraryRole
	removed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
