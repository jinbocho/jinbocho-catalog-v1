from datetime import datetime
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
	genre: Optional[str] = Field(None, description="Normalized genre code")
	genre_raw: Optional[str] = Field(None, description="Original genre text as provided/fetched")
	cover_url: Optional[str] = Field(None, description="Cover image URL")
	notes: Optional[str] = Field(None, description="Notes")
	incipit: Optional[str] = Field(None, description="Presentation/incipit text")
	incipit_source: Optional[str] = Field(None, description="Where the incipit came from")
	incipit_generated_at: Optional[datetime] = Field(None, description="When the incipit was last set")
	created_at: datetime = Field(..., description="Creation timestamp")
	updated_at: datetime = Field(..., description="Last update timestamp")

	class Config:
		from_attributes = True


class GenreCountResponse(BaseModel):
	genre: str = Field(..., description="Normalized genre code")
	count: int = Field(..., description="Number of records with this genre")


class IncipitResponse(BaseModel):
	text: Optional[str] = Field(None, description="Presentation/incipit text, if available")
	source: Optional[str] = Field(None, description="Source: google_books, open_library, manual, ai…")
	generated_at: Optional[datetime] = Field(None, description="When the incipit was set")


class IncipitSetRequest(BaseModel):
	text: str = Field(..., min_length=1, description="Presentation/incipit text")
	source: str = Field("manual", description="Source: 'manual' or 'ai'")
