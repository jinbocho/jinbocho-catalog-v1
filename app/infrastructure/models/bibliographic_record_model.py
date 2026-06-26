from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.session import Base

if TYPE_CHECKING:
    from app.infrastructure.models.owned_book_model import OwnedBookModel


class BibliographicRecordModel(Base):
	__tablename__ = "bibliographic_records"
	__table_args__ = (UniqueConstraint("family_id", "isbn", name="uq_bib_family_isbn"),)

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	title: Mapped[str] = mapped_column(String(500), nullable=False)
	main_author: Mapped[str | None] = mapped_column(String(255))
	other_authors: Mapped[list[str] | None] = mapped_column(ARRAY(String))
	isbn: Mapped[str | None] = mapped_column(String(20), index=True)
	publisher: Mapped[str | None] = mapped_column(String(255))
	publication_year: Mapped[int | None] = mapped_column(Integer)
	language: Mapped[str | None] = mapped_column(String(10))
	genre: Mapped[str | None] = mapped_column(String(100), index=True)
	genre_raw: Mapped[str | None] = mapped_column(String(255))
	cover_url: Mapped[str | None] = mapped_column(Text)
	notes: Mapped[str | None] = mapped_column(Text)
	incipit: Mapped[str | None] = mapped_column(Text)
	incipit_source: Mapped[str | None] = mapped_column(String(20))
	incipit_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
	)

	owned_books: Mapped[list[OwnedBookModel]] = relationship(back_populates="bibliographic_record")
