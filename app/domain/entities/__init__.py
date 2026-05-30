from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class Room:
    family_id: UUID
    name: str
    description: Optional[str] = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Bookcase:
    family_id: UUID
    room_id: UUID
    name: str
    description: Optional[str] = None
    type: Optional[str] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Section:
    bookcase_id: UUID
    section_index: int
    label: Optional[str] = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Shelf:
    section_id: UUID
    shelf_index: int
    notes: Optional[str] = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BibliographicRecord:
    family_id: UUID
    title: str
    main_author: Optional[str] = None
    other_authors: list[str] = field(default_factory=list)
    isbn: Optional[str] = None
    publisher: Optional[str] = None
    publication_year: Optional[int] = None
    language: Optional[str] = None
    genre: Optional[str] = None
    cover_url: Optional[str] = None
    notes: Optional[str] = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class OwnedBook:
    family_id: UUID
    bibliographic_record_id: UUID
    room_id: Optional[UUID] = None
    bookcase_id: Optional[UUID] = None
    section_id: Optional[UUID] = None
    shelf_id: Optional[UUID] = None
    shelf_position: Optional[int] = None
    position_description: Optional[str] = None
    condition: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_price: Optional[Decimal] = None
    source: Optional[str] = None
    reading_status: str = "to_read"
    tags: list[str] = field(default_factory=list)
    notes: Optional[str] = None
    is_intentional_duplicate: bool = False
    duplicate_notes: Optional[str] = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BookHistory:
    owned_book_id: UUID
    event_type: str
    changed_by: UUID
    old_data: Optional[dict] = None
    new_data: Optional[dict] = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
