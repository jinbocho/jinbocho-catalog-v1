from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.api.v1.schemas.record_schemas import BibliographicRecordResponse


class WishlistItemCreate(BaseModel):
    bibliographic_record_id: UUID | None = Field(None, description="Existing record ID")
    title: str | None = Field(None, description="Book title (if no record ID)")
    isbn: str | None = Field(None, description="ISBN (if no record ID)")
    main_author: str | None = Field(None, description="Main author (if no record ID)")
    other_authors: list[str] = Field(default_factory=list)
    publisher: str | None = None
    publication_year: int | None = None
    language: str | None = None
    genre: str | None = None
    cover_url: str | None = None
    notes: str | None = Field(None, max_length=1000, description="Personal notes")
    priority: int | None = Field(None, ge=1, le=3, description="Priority: 1=high, 2=medium, 3=low")

    @field_validator("cover_url")
    @classmethod
    def validate_cover_url(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("cover_url must use http or https scheme")
        return v

    @model_validator(mode="after")
    def require_record_or_title(self) -> "WishlistItemCreate":
        if self.bibliographic_record_id is None and not self.title:
            raise ValueError("Either bibliographic_record_id or title must be provided")
        return self


class WishlistItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Wishlist item ID")
    family_id: UUID = Field(..., description="Family ID")
    user_id: UUID = Field(..., description="User who wants this book")
    bibliographic_record_id: UUID = Field(..., description="Bibliographic record ID")
    added_at: datetime = Field(..., description="When added to wishlist")
    notes: str | None = Field(None, description="Personal notes")
    priority: int | None = Field(None, description="Priority: 1=high, 2=medium, 3=low")
    record: BibliographicRecordResponse = Field(..., description="Bibliographic record details")
