from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.session import Base


class BookClubCycleModel(Base):
    __tablename__ = "book_club_cycles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # No ForeignKey: libraries live in the auth service's database.
    library_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    # FK within the same DB — the record must exist; RESTRICT so a record in an
    # active club cannot be silently deleted.
    bibliographic_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bibliographic_records.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Nullable: the club may read a record no one has shelved. Null the column
    # rather than the whole cycle when the copy is removed.
    owned_book_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("owned_books.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="reading")
    reading_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    reading_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    # No ForeignKey: users live in the auth service's database.
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
