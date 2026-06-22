from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.session import Base


class IsbnLookupCacheModel(Base):
	__tablename__ = "isbn_lookup_cache"

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	isbn: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
	cache_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False)
	source: Mapped[str] = mapped_column(String(50), nullable=False)
	fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
