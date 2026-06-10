from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class OwnedBookCreate(BaseModel):
	bibliographic_record_id: Optional[UUID] = Field(None, description="Bibliographic record ID")
	title: Optional[str] = Field(None, description="Book title (if no record ID)")
	main_author: Optional[str] = Field(None, description="Main author")
	isbn: Optional[str] = Field(None, description="ISBN code")
	room_id: Optional[UUID] = Field(None, description="Room ID")
	bookcase_id: Optional[UUID] = Field(None, description="Bookcase ID")
	section_id: Optional[UUID] = Field(None, description="Section ID")
	shelf_id: Optional[UUID] = Field(None, description="Shelf ID")
	shelf_position: Optional[int] = Field(None, description="Position on shelf")
	condition: Optional[Literal["new", "good", "fair", "poor"]] = Field(None, description="Book condition")
	purchase_date: Optional[date] = Field(None, description="Purchase date")
	purchase_price: Optional[Decimal] = Field(None, description="Purchase price")
	source: Optional[Literal["purchased", "gift", "borrowed", "other"]] = Field(None, description="Source of book")
	reading_status: Literal["to_read", "reading", "read"] = Field("to_read", description="Reading status")
	owner_id: Optional[UUID] = Field(None, description="Family member who owns this copy")
	notes: Optional[str] = Field(None, description="Notes")
	tags: Optional[list[str]] = Field(None, description="Tags")


class OwnedBookUpdate(BaseModel):
	room_id: Optional[UUID] = Field(None, description="Room ID")
	bookcase_id: Optional[UUID] = Field(None, description="Bookcase ID")
	section_id: Optional[UUID] = Field(None, description="Section ID")
	shelf_id: Optional[UUID] = Field(None, description="Shelf ID")
	shelf_position: Optional[int] = Field(None, description="Position on shelf")
	condition: Optional[Literal["new", "good", "fair", "poor"]] = Field(None, description="Book condition")
	purchase_date: Optional[date] = Field(None, description="Purchase date")
	purchase_price: Optional[Decimal] = Field(None, description="Purchase price")
	source: Optional[Literal["purchased", "gift", "borrowed", "other"]] = Field(None, description="Source of book")
	reading_status: Optional[Literal["to_read", "reading", "read"]] = Field(None, description="Reading status")
	owner_id: Optional[UUID] = Field(None, description="Family member who owns this copy")
	tags: Optional[list[str]] = Field(None, description="Tags")
	notes: Optional[str] = Field(None, description="Notes")


class OwnedBookResponse(BaseModel):
	id: UUID = Field(..., description="Book ID")
	family_id: UUID = Field(..., description="Family ID")
	bibliographic_record_id: UUID = Field(..., description="Bibliographic record ID")
	room_id: Optional[UUID] = Field(None, description="Room ID")
	bookcase_id: Optional[UUID] = Field(None, description="Bookcase ID")
	section_id: Optional[UUID] = Field(None, description="Section ID")
	shelf_id: Optional[UUID] = Field(None, description="Shelf ID")
	shelf_position: Optional[int] = Field(None, description="Position on shelf")
	condition: Optional[str] = Field(None, description="Book condition")
	purchase_date: Optional[date] = Field(None, description="Purchase date")
	purchase_price: Optional[Decimal] = Field(None, description="Purchase price")
	source: Optional[str] = Field(None, description="Source of book")
	reading_status: str = Field(..., description="Reading status")
	current_reader_id: Optional[UUID] = Field(None, description="User currently reading the copy")
	owner_id: Optional[UUID] = Field(None, description="Family member who owns this copy")
	notes: Optional[str] = Field(None, description="Notes")
	tags: list[str] = Field(..., description="Tags")
	created_at: datetime = Field(..., description="Creation timestamp")
	updated_at: datetime = Field(..., description="Last update timestamp")

	class Config:
		from_attributes = True


class BookReadCreate(BaseModel):
	user_id: UUID = Field(..., description="User ID to mark as having read the book")


class BookReadResponse(BaseModel):
	owned_book_id: UUID = Field(..., description="Book ID")
	user_id: UUID = Field(..., description="User ID")
	read_at: datetime = Field(..., description="When the member finished reading")

	class Config:
		from_attributes = True


class BookLoanCreate(BaseModel):
	borrower_name: str = Field(..., min_length=1, max_length=255, description="Name of the person borrowing the book")
	due_date: Optional[datetime] = Field(None, description="Expected return date")


class BookLoanResponse(BaseModel):
	id: UUID = Field(..., description="Loan ID")
	owned_book_id: UUID = Field(..., description="Book ID")
	borrower_name: str = Field(..., description="Name of the borrower")
	loaned_at: datetime = Field(..., description="When the book was lent")
	due_date: Optional[datetime] = Field(None, description="Expected return date")
	returned_at: Optional[datetime] = Field(None, description="When the book was returned (null = still on loan)")

	class Config:
		from_attributes = True
