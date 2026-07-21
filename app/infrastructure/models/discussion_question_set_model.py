from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.session import Base


class DiscussionQuestionSetModel(Base):
    __tablename__ = "discussion_question_sets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # One set per book — no separate uniqueness needed, find_by_book only
    # ever expects at most one row (enforced by the unique index below).
    owned_book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("owned_books.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    questions: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
