from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExportedRecordInfo(BaseModel):
	id: UUID
	title: str
	main_author: Optional[str] = None
	other_authors: list[str] = Field(default_factory=list)
	isbn: Optional[str] = None
	publisher: Optional[str] = None
	publication_year: Optional[int] = None
	language: Optional[str] = None
	genre: Optional[str] = None
	cover_url: Optional[str] = None
	notes: Optional[str] = None


class ExportedLocationInfo(BaseModel):
	room_id: Optional[UUID] = None
	room_name: Optional[str] = None
	bookcase_id: Optional[UUID] = None
	bookcase_name: Optional[str] = None
	section_id: Optional[UUID] = None
	section_index: Optional[int] = None
	section_label: Optional[str] = None
	shelf_id: Optional[UUID] = None
	shelf_index: Optional[int] = None
	shelf_notes: Optional[str] = None
	shelf_position: Optional[int] = None
	position_description: Optional[str] = None


class ExportedReaderInfo(BaseModel):
	user_id: UUID
	read_at: datetime


class ExportedLoanInfo(BaseModel):
	borrower_name: str
	loaned_at: datetime
	due_date: Optional[datetime] = None


class ExportedBookResponse(BaseModel):
	id: UUID = Field(..., description="Book ID")
	record: Optional[ExportedRecordInfo] = Field(None, description="Bibliographic metadata")
	reading_status: str = Field(..., description="Reading status")
	condition: Optional[str] = None
	source: Optional[str] = None
	purchase_date: Optional[date] = None
	purchase_price: Optional[Decimal] = None
	owner_id: Optional[UUID] = Field(None, description="Family member who owns this copy")
	current_reader_id: Optional[UUID] = Field(None, description="Who is currently reading it")
	tags: list[str] = Field(default_factory=list)
	notes: Optional[str] = None
	is_intentional_duplicate: bool = False
	duplicate_notes: Optional[str] = None
	location: ExportedLocationInfo = Field(default_factory=ExportedLocationInfo)
	readers: list[ExportedReaderInfo] = Field(default_factory=list, description="All who have read this copy")
	active_loan: Optional[ExportedLoanInfo] = Field(None, description="Current active loan, if any")
	created_at: datetime
	updated_at: datetime


# ── Full library backup / restore ───────────────────────────────────────────
# Unlike ExportedBookResponse above (denormalized, books-only, lossy), these
# mirror each domain entity 1:1 for a complete, round-trippable snapshot.


class RoomExportItem(BaseModel):
	id: UUID
	name: str
	description: Optional[str] = None


class BookcaseExportItem(BaseModel):
	id: UUID
	room_id: UUID
	name: str
	description: Optional[str] = None
	type: Optional[str] = None
	notes: Optional[str] = None
	image_url: Optional[str] = None


class SectionExportItem(BaseModel):
	id: UUID
	bookcase_id: UUID
	section_index: int
	label: Optional[str] = None


class ShelfExportItem(BaseModel):
	id: UUID
	section_id: UUID
	shelf_index: int
	notes: Optional[str] = None


class BibliographicRecordExportItem(BaseModel):
	id: UUID
	title: str
	main_author: Optional[str] = None
	other_authors: list[str] = Field(default_factory=list)
	isbn: Optional[str] = None
	publisher: Optional[str] = None
	publication_year: Optional[int] = None
	language: Optional[str] = None
	genre: Optional[str] = None
	genre_raw: Optional[str] = None
	cover_url: Optional[str] = None
	notes: Optional[str] = None
	incipit: Optional[str] = None
	incipit_source: Optional[str] = None
	incipit_generated_at: Optional[datetime] = None


class OwnedBookExportItem(BaseModel):
	id: UUID
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
	current_reader_id: Optional[UUID] = None
	owner_id: Optional[UUID] = None
	tags: list[str] = Field(default_factory=list)
	notes: Optional[str] = None
	is_intentional_duplicate: bool = False
	duplicate_notes: Optional[str] = None
	created_at: datetime
	updated_at: datetime


class BookReadExportItem(BaseModel):
	id: UUID
	owned_book_id: UUID
	user_id: UUID
	read_at: datetime


class BookLoanExportItem(BaseModel):
	id: UUID
	owned_book_id: UUID
	borrower_name: str
	loaned_at: datetime
	due_date: Optional[datetime] = None
	returned_at: Optional[datetime] = None


class BookHistoryExportItem(BaseModel):
	id: UUID
	owned_book_id: UUID
	event_type: str
	changed_by: UUID
	old_data: Optional[dict[str, Any]] = None
	new_data: Optional[dict[str, Any]] = None
	created_at: datetime


class RemovedMemberExportItem(BaseModel):
	"""A former family member's identity, snapshotted when they were removed
	from the family (see POST /v1/members/removed) — so a future import can
	recreate their real account instead of leaving owner_id/etc. unresolved."""
	id: UUID
	full_name: str
	email: str
	role: str
	removed_at: datetime


class RecordRemovedMemberRequest(BaseModel):
	id: UUID = Field(description="The auth-service user id being removed")
	full_name: str
	email: str
	role: str = Field(pattern="^(admin|editor|viewer)$")


class FullLibraryExportResponse(BaseModel):
	schema_version: int = 1
	exported_at: datetime
	rooms: list[RoomExportItem]
	bookcases: list[BookcaseExportItem]
	sections: list[SectionExportItem]
	shelves: list[ShelfExportItem]
	bibliographic_records: list[BibliographicRecordExportItem]
	owned_books: list[OwnedBookExportItem]
	book_reads: list[BookReadExportItem]
	book_loans: list[BookLoanExportItem]
	book_history: list[BookHistoryExportItem]
	removed_members: list[RemovedMemberExportItem] = Field(default_factory=list)


class ImportFullLibraryRequest(BaseModel):
	rooms: list[RoomExportItem] = Field(default_factory=list)
	bookcases: list[BookcaseExportItem] = Field(default_factory=list)
	sections: list[SectionExportItem] = Field(default_factory=list)
	shelves: list[ShelfExportItem] = Field(default_factory=list)
	bibliographic_records: list[BibliographicRecordExportItem] = Field(default_factory=list)
	owned_books: list[OwnedBookExportItem] = Field(default_factory=list)
	book_reads: list[BookReadExportItem] = Field(default_factory=list)
	book_loans: list[BookLoanExportItem] = Field(default_factory=list)
	book_history: list[BookHistoryExportItem] = Field(default_factory=list)
	user_id_map: dict[str, str] = Field(
		default_factory=dict,
		description="Original user id -> matched-or-created user id, from POST /v1/users/import on the auth service",
	)

	model_config = ConfigDict(json_schema_extra={"example": {"rooms": [], "owned_books": [], "user_id_map": {}}})


class ImportFullLibraryResponse(BaseModel):
	rooms_imported: int
	rooms_deduped: int
	bookcases_imported: int
	bookcases_deduped: int
	sections_imported: int
	sections_deduped: int
	shelves_imported: int
	shelves_deduped: int
	records_imported: int
	records_deduped: int
	owned_books_imported: int
	owned_books_deduped: int
	book_reads_imported: int
	book_loans_imported: int
	book_history_imported: int
