from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.session import Base


class BookClubQuestionSetModel(Base):
    __tablename__ = "book_club_question_sets"
    __table_args__ = (
        # One set per cycle AND language: switching UI language yields a fresh set
        # in the new language rather than the stale cached one.
        UniqueConstraint("cycle_id", "language", name="uq_book_club_question_sets_cycle_language"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cycle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("book_club_cycles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # "" when the reader language was unknown at generation time.
    language: Mapped[str] = mapped_column(String(8), nullable=False, server_default="")
    questions: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
