from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExportedRecordInfo(BaseModel):
	id: UUID
	title: str
	main_author: str | None = None
	other_authors: list[str] = Field(default_factory=list)
	isbn: str | None = None
	publisher: str | None = None
	publication_year: int | None = None
	language: str | None = None
	genre: str | None = None
	cover_url: str | None = None
	notes: str | None = None


class ExportedLocationInfo(BaseModel):
	room_id: UUID | None = None
	room_name: str | None = None
	bookcase_id: UUID | None = None
	bookcase_name: str | None = None
	section_id: UUID | None = None
	section_index: int | None = None
	section_label: str | None = None
	shelf_id: UUID | None = None
	shelf_index: int | None = None
	shelf_notes: str | None = None
	shelf_position: int | None = None
	position_description: str | None = None


class ExportedReaderInfo(BaseModel):
	user_id: UUID
	read_at: datetime


class ExportedLoanInfo(BaseModel):
	borrower_name: str
	loaned_at: datetime
	due_date: datetime | None = None


class ExportedBookResponse(BaseModel):
	id: UUID = Field(..., description="Book ID")
	record: ExportedRecordInfo | None = Field(None, description="Bibliographic metadata")
	reading_status: str = Field(..., description="Reading status")
	condition: str | None = None
	source: str | None = None
	purchase_date: date | None = None
	purchase_price: Decimal | None = None
	owner_id: UUID | None = Field(None, description="Family member who owns this copy")
	current_reader_id: UUID | None = Field(None, description="Who is currently reading it")
	tags: list[str] = Field(default_factory=list)
	notes: str | None = None
	is_intentional_duplicate: bool = False
	duplicate_notes: str | None = None
	location: ExportedLocationInfo = Field(default_factory=ExportedLocationInfo)
	readers: list[ExportedReaderInfo] = Field(default_factory=list, description="All who have read this copy")
	active_loan: ExportedLoanInfo | None = Field(None, description="Current active loan, if any")
	created_at: datetime
	updated_at: datetime


# ── Full library backup / restore ───────────────────────────────────────────
# Unlike ExportedBookResponse above (denormalized, books-only, lossy), these
# mirror each domain entity 1:1 for a complete, round-trippable snapshot.


class RoomExportItem(BaseModel):
	id: UUID
	name: str
	description: str | None = None


class BookcaseExportItem(BaseModel):
	id: UUID
	room_id: UUID
	name: str
	description: str | None = None
	type: str | None = None
	notes: str | None = None
	image_url: str | None = None


class SectionExportItem(BaseModel):
	id: UUID
	bookcase_id: UUID
	section_index: int
	label: str | None = None


class ShelfExportItem(BaseModel):
	id: UUID
	section_id: UUID
	shelf_index: int
	notes: str | None = None


class BibliographicRecordExportItem(BaseModel):
	id: UUID
	title: str
	main_author: str | None = None
	other_authors: list[str] = Field(default_factory=list)
	isbn: str | None = None
	publisher: str | None = None
	publication_year: int | None = None
	language: str | None = None
	genre: str | None = None
	genre_raw: str | None = None
	cover_url: str | None = None
	notes: str | None = None
	incipit: str | None = None
	incipit_source: str | None = None
	incipit_generated_at: datetime | None = None


class OwnedBookExportItem(BaseModel):
	id: UUID
	bibliographic_record_id: UUID
	room_id: UUID | None = None
	bookcase_id: UUID | None = None
	section_id: UUID | None = None
	shelf_id: UUID | None = None
	shelf_position: int | None = None
	position_description: str | None = None
	condition: str | None = None
	purchase_date: date | None = None
	purchase_price: Decimal | None = None
	source: str | None = None
	reading_status: str = "to_read"
	current_reader_id: UUID | None = None
	owner_id: UUID | None = None
	tags: list[str] = Field(default_factory=list)
	notes: str | None = None
	is_intentional_duplicate: bool = False
	duplicate_notes: str | None = None
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
	due_date: datetime | None = None
	returned_at: datetime | None = None


class BookHistoryExportItem(BaseModel):
	id: UUID
	owned_book_id: UUID
	event_type: str
	changed_by: UUID
	old_data: dict[str, Any] | None = None
	new_data: dict[str, Any] | None = None
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


class DeleteFamilyDataResponse(BaseModel):
	"""Counts of what was permanently wiped — for the admin's own confirmation
	toast. This is the catalog-service half of full account deletion; the
	frontend must also call auth-service's DELETE /v1/families/{family_id}."""
	rooms_deleted: int
	bookcases_deleted: int
	records_deleted: int
	owned_books_deleted: int
	removed_members_deleted: int
