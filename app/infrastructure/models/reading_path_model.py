from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.session import Base


class ReadingPathModel(Base):
    __tablename__ = "reading_paths"
    __table_args__ = (CheckConstraint("source IN ('manual','ai')", name="ck_reading_paths_source"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # No ForeignKey: libraries live in the auth service's database.
    library_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # No per-element FK — same convention as quiz_attempts.question_ids: an
    # owned_book_id later deleted simply drops off the path silently, which
    # is the desired behavior (never a broken reference the FE has to guard).
    book_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    target_band: Mapped[str | None] = mapped_column(String(10), nullable=True)
    source: Mapped[str] = mapped_column(String(10), nullable=False, server_default="manual")
    # No ForeignKey: users live in the auth service's database.
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
