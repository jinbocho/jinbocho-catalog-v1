from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.session import Base


class BookClubPostModel(Base):
    __tablename__ = "book_club_posts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # FK within the same DB — cascade delete when the cycle is removed.
    cycle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("book_club_cycles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # No ForeignKey: users live in the auth service's database.
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Self-referential thread parent; cascade so deleting a post drops its replies.
    parent_post_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("book_club_posts.id", ondelete="CASCADE"),
        nullable=True,
    )
    is_spoiler: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
