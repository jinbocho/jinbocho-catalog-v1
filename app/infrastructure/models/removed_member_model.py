from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.session import Base


class RemovedMemberModel(Base):
	__tablename__ = "removed_members"

	# Primary key is the ORIGINAL auth-service user id, not a fresh one — it's
	# the join key used to resolve owner_id/current_reader_id/etc. on export.
	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
	family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
	full_name: Mapped[str] = mapped_column(String(255), nullable=False)
	email: Mapped[str] = mapped_column(String(255), nullable=False)
	role: Mapped[str] = mapped_column(String(20), nullable=False)
	removed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
