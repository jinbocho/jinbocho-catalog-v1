import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.session import Base

reading_status_enum = Enum("to_read", "reading", "read", name="reading_status")
book_condition_enum = Enum("new", "good", "fair", "poor", name="book_condition")
book_source_enum = Enum("purchased", "gift", "borrowed", "other", name="book_source")
book_event_type_enum = Enum(
    "created",
    "metadata_updated",
    "position_changed",
    "reading_status_changed",
    "deleted",
    name="book_event_type",
)


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


class BookcaseModel(Base):
    __tablename__ = "bookcases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    room_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    room: Mapped["RoomModel"] = relationship(back_populates="bookcases")
    sections: Mapped[list["SectionModel"]] = relationship(back_populates="bookcase", order_by="SectionModel.section_index")


class SectionModel(Base):
    __tablename__ = "sections"
    __table_args__ = (UniqueConstraint("bookcase_id", "section_index"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bookcase_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bookcases.id", ondelete="CASCADE"), nullable=False, index=True)
    section_index: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    bookcase: Mapped["BookcaseModel"] = relationship(back_populates="sections")
    shelves: Mapped[list["ShelfModel"]] = relationship(back_populates="section", order_by="ShelfModel.shelf_index")


class ShelfModel(Base):
    __tablename__ = "shelves"
    __table_args__ = (UniqueConstraint("section_id", "shelf_index"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    section_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sections.id", ondelete="CASCADE"), nullable=False, index=True)
    shelf_index: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    section: Mapped["SectionModel"] = relationship(back_populates="shelves")
    books: Mapped[list["OwnedBookModel"]] = relationship(back_populates="shelf", foreign_keys="[OwnedBookModel.shelf_id]")


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
    genre: Mapped[str | None] = mapped_column(String(100))
    cover_url: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    owned_books: Mapped[list["OwnedBookModel"]] = relationship(back_populates="bibliographic_record")


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


class BookHistoryModel(Base):
    __tablename__ = "book_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Intentionally no ForeignKey — audit records are retained even after the book is deleted
    owned_book_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(book_event_type_enum, nullable=False)
    changed_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    old_data: Mapped[dict | None] = mapped_column(JSONB)
    new_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IsbnLookupCacheModel(Base):
    __tablename__ = "isbn_lookup_cache"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    isbn: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    cache_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
