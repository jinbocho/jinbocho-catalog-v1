from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.session import Base


class ShelfModel(Base):
	__tablename__ = "shelves"
	__table_args__ = (UniqueConstraint("section_id", "shelf_index"),)

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	section_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("sections.id", ondelete="CASCADE"), nullable=False, index=True
	)
	shelf_index: Mapped[int] = mapped_column(Integer, nullable=False)
	notes: Mapped[str | None] = mapped_column(Text)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
	)

	section: Mapped["SectionModel"] = relationship(back_populates="shelves")
	books: Mapped[list["OwnedBookModel"]] = relationship(back_populates="shelf", foreign_keys="[OwnedBookModel.shelf_id]")
