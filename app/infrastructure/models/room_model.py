from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.session import Base


class RoomModel(Base):
	__tablename__ = "rooms"

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	name: Mapped[str] = mapped_column(String(255), nullable=False)
	description: Mapped[str | None] = mapped_column(Text)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
	)

	bookcases: Mapped[list["BookcaseModel"]] = relationship(back_populates="room")
