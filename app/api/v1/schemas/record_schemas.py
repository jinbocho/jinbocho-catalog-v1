from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BibliographicRecordCreate(BaseModel):
	title: str = Field(..., description="Book title")
	main_author: Optional[str] = Field(None, description="Main author name")
	other_authors: Optional[list[str]] = Field(None, description="Other authors")
	isbn: Optional[str] = Field(None, description="ISBN code")
	publisher: Optional[str] = Field(None, description="Publisher name")
	publication_year: Optional[int] = Field(None, description="Year of publication")
	language: Optional[str] = Field(None, description="Language code (e.g., en, it)")
	genre: Optional[str] = Field(None, description="Genre")
	cover_url: Optional[str] = Field(None, description="Cover image URL")
	notes: Optional[str] = Field(None, description="Notes")


class BibliographicRecordUpdate(BaseModel):
	title: Optional[str] = Field(None, description="Book title")
	main_author: Optional[str] = Field(None, description="Main author name")
	other_authors: Optional[list[str]] = Field(None, description="Other authors")
	isbn: Optional[str] = Field(None, description="ISBN code")
	publisher: Optional[str] = Field(None, description="Publisher name")
	publication_year: Optional[int] = Field(None, description="Year of publication")
	language: Optional[str] = Field(None, description="Language code")
	genre: Optional[str] = Field(None, description="Genre")
	cover_url: Optional[str] = Field(None, description="Cover image URL")
	notes: Optional[str] = Field(None, description="Notes")


class BibliographicRecordResponse(BaseModel):
	id: UUID = Field(..., description="Record ID")
	family_id: UUID = Field(..., description="Family ID")
	title: str = Field(..., description="Book title")
	main_author: Optional[str] = Field(None, description="Main author name")
	other_authors: list[str] = Field(..., description="Other authors")
	isbn: Optional[str] = Field(None, description="ISBN code")
	publisher: Optional[str] = Field(None, description="Publisher name")
	publication_year: Optional[int] = Field(None, description="Year of publication")
	language: Optional[str] = Field(None, description="Language code")
	genre: Optional[str] = Field(None, description="Genre")
	cover_url: Optional[str] = Field(None, description="Cover image URL")
	notes: Optional[str] = Field(None, description="Notes")
	created_at: str = Field(..., description="Creation timestamp")
	updated_at: str = Field(..., description="Last update timestamp")

	class Config:
		from_attributes = True
