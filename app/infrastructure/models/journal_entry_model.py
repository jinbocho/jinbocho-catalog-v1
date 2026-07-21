from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.session import Base


class JournalEntryModel(Base):
    __tablename__ = "journal_entries"
    __table_args__ = (
        CheckConstraint("prompt_kind IN ('free','retelling','creative')", name="ck_journal_entries_prompt_kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # FK within the same DB — cascade delete when the book is removed.
    owned_book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("owned_books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # No ForeignKey: users (including child accounts) live in the auth service's database.
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_kind: Mapped[str] = mapped_column(String(10), nullable=False, server_default="free")
    emoji: Mapped[str | None] = mapped_column(String(8), nullable=True)
    # Same-DB FK, unlike user_id/owned_book_id — SET NULL so deleting the
    # session (unusual, but possible) doesn't take the entry with it.
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reading_sessions.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
