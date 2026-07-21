from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.session import Base


class BookClubVoteModel(Base):
    __tablename__ = "book_club_votes"
    __table_args__ = (
        UniqueConstraint("proposal_id", "user_id", name="uq_book_club_votes_proposal_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("book_club_proposals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # No ForeignKey: users live in the auth service's database.
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
