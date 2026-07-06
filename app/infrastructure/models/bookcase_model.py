from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.session import Base

if TYPE_CHECKING:
    from app.infrastructure.models.room_model import RoomModel
    from app.infrastructure.models.section_model import SectionModel


class BookcaseModel(Base):
	__tablename__ = "bookcases"

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	library_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	room_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False, index=True
	)
	name: Mapped[str] = mapped_column(String(255), nullable=False)
	description: Mapped[str | None] = mapped_column(Text)
	type: Mapped[str | None] = mapped_column(String(100))
	notes: Mapped[str | None] = mapped_column(Text)
	image_url: Mapped[str | None] = mapped_column(Text)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
	)

	room: Mapped[RoomModel] = relationship(back_populates="bookcases")
	sections: Mapped[list[SectionModel]] = relationship(
		back_populates="bookcase", order_by="SectionModel.section_index"
	)
