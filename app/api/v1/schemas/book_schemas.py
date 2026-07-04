from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.entities import BookCondition, BookSource, ReadingStatus


class DuplicateBookConflictResponse(BaseModel):
	"""409 body for POST /v1/books/ when the family already owns this book.
	The check is family-wide, not scoped to an owner (two members can each
	legitimately have a copy) — existing_owner_id/location say who already
	has it and where. Resubmit with is_intentional_duplicate=true to add it
	anyway."""
	error: Literal["duplicate_book"] = "duplicate_book"
	conflict_type: Literal["isbn_match", "title_author_match", "fuzzy_match"]
	existing_book_id: UUID
	existing_record_id: UUID
	title: str
	main_author: str | None = None
	isbn: str | None = None
	existing_owner_id: UUID | None = None
	existing_room_id: UUID | None = None
	existing_bookcase_id: UUID | None = None
	existing_section_id: UUID | None = None
	existing_shelf_id: UUID | None = None
	match_reason: str | None = None


class OwnedBookCreate(BaseModel):
	bibliographic_record_id: UUID | None = Field(None, description="Bibliographic record ID")
	title: str | None = Field(None, description="Book title (if no record ID)")
	main_author: str | None = Field(None, description="Main author")
	isbn: str | None = Field(None, description="ISBN code")
	room_id: UUID | None = Field(None, description="Room ID")
	bookcase_id: UUID | None = Field(None, description="Bookcase ID")
	section_id: UUID | None = Field(None, description="Section ID")
	shelf_id: UUID | None = Field(None, description="Shelf ID")
	shelf_position: int | None = Field(None, description="Position on shelf")
	condition: BookCondition | None = Field(None, description="Book condition")
	purchase_date: date | None = Field(None, description="Purchase date")
	purchase_price: Decimal | None = Field(None, description="Purchase price")
	source: BookSource | None = Field(None, description="Source of book")
	reading_status: ReadingStatus = Field(ReadingStatus.TO_READ, description="Reading status")
	owner_id: UUID | None = Field(None, description="Family member who owns this copy")
	notes: str | None = Field(None, description="Notes")
	tags: list[str] | None = Field(None, description="Tags")
	is_intentional_duplicate: bool = Field(
		False,
		description="Set to true to confirm adding this book despite a duplicate warning "
		"(409 DUPLICATE_BOOK) from a previous call with the same data.",
	)


class OwnedBookUpdate(BaseModel):
	room_id: UUID | None = Field(None, description="Room ID")
	bookcase_id: UUID | None = Field(None, description="Bookcase ID")
	section_id: UUID | None = Field(None, description="Section ID")
	shelf_id: UUID | None = Field(None, description="Shelf ID")
	shelf_position: int | None = Field(None, description="Position on shelf")
	condition: BookCondition | None = Field(None, description="Book condition")
	purchase_date: date | None = Field(None, description="Purchase date")
	purchase_price: Decimal | None = Field(None, description="Purchase price")
	source: BookSource | None = Field(None, description="Source of book")
	reading_status: ReadingStatus | None = Field(None, description="Reading status")
	owner_id: UUID | None = Field(None, description="Family member who owns this copy")
	tags: list[str] | None = Field(None, description="Tags")
	notes: str | None = Field(None, description="Notes")


class OwnedBookResponse(BaseModel):
	id: UUID = Field(..., description="Book ID")
	family_id: UUID = Field(..., description="Family ID")
	bibliographic_record_id: UUID = Field(..., description="Bibliographic record ID")
	room_id: UUID | None = Field(None, description="Room ID")
	bookcase_id: UUID | None = Field(None, description="Bookcase ID")
	section_id: UUID | None = Field(None, description="Section ID")
	shelf_id: UUID | None = Field(None, description="Shelf ID")
	shelf_position: int | None = Field(None, description="Position on shelf")
	condition: str | None = Field(None, description="Book condition")
	purchase_date: date | None = Field(None, description="Purchase date")
	purchase_price: Decimal | None = Field(None, description="Purchase price")
	source: str | None = Field(None, description="Source of book")
	reading_status: str = Field(..., description="Reading status")
	current_reader_id: UUID | None = Field(None, description="User currently reading the copy")
	owner_id: UUID | None = Field(None, description="Family member who owns this copy")
	notes: str | None = Field(None, description="Notes")
	tags: list[str] = Field(..., description="Tags")
	is_intentional_duplicate: bool = Field(False, description="True if added despite a duplicate warning")
	created_at: datetime = Field(..., description="Creation timestamp")
	updated_at: datetime = Field(..., description="Last update timestamp")

	class Config:
		from_attributes = True


class BookReadCreate(BaseModel):
	user_id: UUID = Field(..., description="User ID to mark as having read the book")
	read_at: datetime | None = Field(None, description="Month-precision read date; defaults to now if omitted")


class BookReadResponse(BaseModel):
	owned_book_id: UUID = Field(..., description="Book ID")
	user_id: UUID = Field(..., description="User ID")
	read_at: datetime = Field(..., description="When the member finished reading")

	class Config:
		from_attributes = True


class BookRatingCreate(BaseModel):
	rating: int = Field(..., ge=1, le=5, description="Star rating from 1 (lowest) to 5 (highest)")
	review: str | None = Field(None, max_length=4000, description="Optional textual review")


class BookRatingUpdate(BaseModel):
	rating: int | None = Field(None, ge=1, le=5, description="Updated star rating")
	review: str | None = Field(None, max_length=4000, description="Updated review text")


class BookRatingResponse(BaseModel):
	id: UUID = Field(..., description="Rating ID")
	owned_book_id: UUID = Field(..., description="Book copy ID")
	user_id: UUID = Field(..., description="User who submitted the rating")
	rating: int = Field(..., description="Star rating (1-5)")
	review: str | None = Field(None, description="Optional review text")
	created_at: datetime = Field(..., description="When the rating was created")
	updated_at: datetime = Field(..., description="When the rating was last updated")

	class Config:
		from_attributes = True


class FamilyRatingStatsResponse(BaseModel):
	owned_book_id: UUID = Field(..., description="Book copy ID")
	total: int = Field(..., description="Total number of ratings")
	average: float | None = Field(None, description="Average star rating, null when no ratings exist")
	distribution: dict[int, int] = Field(..., description="Count of ratings per star value (1-5)")


class BulkDeleteBooksRequest(BaseModel):
	book_ids: list[UUID] = Field(
		...,
		min_length=1,
		max_length=200,
		description="Book IDs to delete. All-or-nothing: if any ID is missing or belongs to another family, "
		"none are deleted.",
	)


class BulkDeleteBooksResponse(BaseModel):
	deleted: int = Field(..., description="Number of books deleted")


class BookLoanCreate(BaseModel):
	borrower_name: str = Field(..., min_length=1, max_length=255, description="Name of the person borrowing the book")
	due_date: datetime | None = Field(None, description="Expected return date")


class BookLoanResponse(BaseModel):
	id: UUID = Field(..., description="Loan ID")
	owned_book_id: UUID = Field(..., description="Book ID")
	borrower_name: str = Field(..., description="Name of the borrower")
	loaned_at: datetime = Field(..., description="When the book was lent")
	due_date: datetime | None = Field(None, description="Expected return date")
	returned_at: datetime | None = Field(None, description="When the book was returned (null = still on loan)")

	class Config:
		from_attributes = True
