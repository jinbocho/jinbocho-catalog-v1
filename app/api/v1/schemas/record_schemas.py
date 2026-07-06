from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _validate_http_url(v: str | None) -> str | None:
	if v is not None and not v.startswith(("http://", "https://")):
		raise ValueError("must use http or https scheme")
	return v


class BibliographicRecordCreate(BaseModel):
	title: str = Field(..., description="Book title")
	main_author: str | None = Field(None, description="Main author name")
	other_authors: list[str] | None = Field(None, description="Other authors")
	isbn: str | None = Field(None, description="ISBN code")
	publisher: str | None = Field(None, description="Publisher name")
	publication_year: int | None = Field(None, description="Year of publication")
	language: str | None = Field(None, description="Language code (e.g., en, it)")
	genre: str | None = Field(None, description="Genre")
	cover_url: str | None = Field(None, description="Cover image URL")
	notes: str | None = Field(None, description="Notes")

	@field_validator("cover_url")
	@classmethod
	def validate_cover_url(cls, v: str | None) -> str | None:
		return _validate_http_url(v)


class BibliographicRecordUpdate(BaseModel):
	title: str | None = Field(None, description="Book title")
	main_author: str | None = Field(None, description="Main author name")
	other_authors: list[str] | None = Field(None, description="Other authors")
	isbn: str | None = Field(None, description="ISBN code")
	publisher: str | None = Field(None, description="Publisher name")
	publication_year: int | None = Field(None, description="Year of publication")
	language: str | None = Field(None, description="Language code")
	genre: str | None = Field(None, description="Genre")
	cover_url: str | None = Field(None, description="Cover image URL")
	notes: str | None = Field(None, description="Notes")

	@field_validator("cover_url")
	@classmethod
	def validate_cover_url(cls, v: str | None) -> str | None:
		return _validate_http_url(v)


class BibliographicRecordResponse(BaseModel):
	id: UUID = Field(..., description="Record ID")
	library_id: UUID = Field(..., description="Library ID")
	title: str = Field(..., description="Book title")
	main_author: str | None = Field(None, description="Main author name")
	other_authors: list[str] = Field(..., description="Other authors")
	isbn: str | None = Field(None, description="ISBN code")
	publisher: str | None = Field(None, description="Publisher name")
	publication_year: int | None = Field(None, description="Year of publication")
	language: str | None = Field(None, description="Language code")
	genre: str | None = Field(None, description="Normalized genre code")
	genre_raw: str | None = Field(None, description="Original genre text as provided/fetched")
	cover_url: str | None = Field(None, description="Cover image URL")
	notes: str | None = Field(None, description="Notes")
	incipit: str | None = Field(None, description="Presentation/incipit text")
	incipit_source: str | None = Field(None, description="Where the incipit came from")
	incipit_generated_at: datetime | None = Field(None, description="When the incipit was last set")
	created_at: datetime = Field(..., description="Creation timestamp")
	updated_at: datetime = Field(..., description="Last update timestamp")

	model_config = ConfigDict(from_attributes=True)


class GenreCountResponse(BaseModel):
	genre: str = Field(..., description="Normalized genre code")
	count: int = Field(..., description="Number of records with this genre")


class IncipitResponse(BaseModel):
	text: str | None = Field(None, description="Presentation/incipit text, if available")
	source: str | None = Field(None, description="Source: google_books, open_library, manual, ai…")
	generated_at: datetime | None = Field(None, description="When the incipit was set")


class IncipitSetRequest(BaseModel):
	text: str = Field(..., min_length=1, description="Presentation/incipit text")
	source: str = Field("manual", description="Source: 'manual' or 'ai'")
