from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.session import Base


class SectionModel(Base):
	__tablename__ = "sections"
	__table_args__ = (UniqueConstraint("bookcase_id", "section_index"),)

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	bookcase_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("bookcases.id", ondelete="CASCADE"), nullable=False, index=True
	)
	section_index: Mapped[int] = mapped_column(Integer, nullable=False)
	label: Mapped[str | None] = mapped_column(String(100))
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
	)

	bookcase: Mapped[BookcaseModel] = relationship(back_populates="sections")
	shelves: Mapped[list[ShelfModel]] = relationship(back_populates="section", order_by="ShelfModel.shelf_index")
