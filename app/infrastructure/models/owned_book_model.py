from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.session import Base
from app.infrastructure.models.enums import book_condition_enum, book_source_enum, reading_status_enum


class OwnedBookModel(Base):
	__tablename__ = "owned_books"

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	bibliographic_record_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("bibliographic_records.id", ondelete="RESTRICT"), nullable=False, index=True
	)
	room_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="SET NULL"))
	bookcase_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("bookcases.id", ondelete="SET NULL"))
	section_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sections.id", ondelete="SET NULL"))
	shelf_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("shelves.id", ondelete="SET NULL"), index=True)
	shelf_position: Mapped[int | None] = mapped_column(Integer)
	position_description: Mapped[str | None] = mapped_column(Text)
	condition: Mapped[str | None] = mapped_column(book_condition_enum)
	purchase_date: Mapped[date | None] = mapped_column(Date)
	purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
	source: Mapped[str | None] = mapped_column(book_source_enum)
	reading_status: Mapped[str] = mapped_column(reading_status_enum, nullable=False, server_default="to_read", index=True)
	tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
	notes: Mapped[str | None] = mapped_column(Text)
	is_intentional_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
	duplicate_notes: Mapped[str | None] = mapped_column(Text)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
	)

	bibliographic_record: Mapped["BibliographicRecordModel"] = relationship(back_populates="owned_books")
	shelf: Mapped["ShelfModel | None"] = relationship(back_populates="books", foreign_keys=[shelf_id])
