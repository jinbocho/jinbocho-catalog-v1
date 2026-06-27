from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class WishlistItem:
    family_id: UUID
    user_id: UUID
    bibliographic_record_id: UUID
    added_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    notes: str | None = None
    priority: int | None = None  # 1=high, 2=medium, 3=low
    id: UUID = field(default_factory=uuid4)
