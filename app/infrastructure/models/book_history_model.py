from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.session import Base
from app.infrastructure.models.enums import book_event_type_enum


class BookHistoryModel(Base):
	__tablename__ = "book_history"

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	# Intentionally no ForeignKey — audit records are retained even after the book is deleted
	owned_book_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	event_type: Mapped[str] = mapped_column(book_event_type_enum, nullable=False)
	changed_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
	old_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
	new_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
