from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


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
