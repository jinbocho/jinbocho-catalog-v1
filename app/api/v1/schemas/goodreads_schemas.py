from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.entities import ReadingStatus

# A Goodreads export with tens of thousands of books is still well under 5MB
# of CSV text; the cap only guards abuse, well below the gateway's 10MB limit.
_MAX_CSV_LENGTH = 5_000_000


class GoodreadsPreviewRequest(BaseModel):
	csv_text: str = Field(
		..., min_length=1, max_length=_MAX_CSV_LENGTH, description="Raw contents of the Goodreads export CSV"
	)


class GoodreadsPreviewRowResponse(BaseModel):
	row_number: int = Field(..., description="1-based position in the CSV")
	status: Literal["new", "already_owned", "invalid"] = Field(
		...,
		description="new: not yet owned. already_owned: matches a book the library already has. "
		"invalid: missing a title, cannot be imported.",
	)
	title: str
	main_author: str | None = None
	other_authors: list[str] = Field(default_factory=list)
	isbn: str | None = None
	publisher: str | None = None
	publication_year: int | None = None
	reading_status: ReadingStatus
	rating: int | None = Field(
		None, description="My Rating from the CSV, 1-5; omitted when Goodreads recorded 0 (unrated)"
	)
	review: str | None = None
	read_at: datetime | None = Field(None, description="Date Read from the CSV, when the shelf is 'read'")
	tags: list[str] = Field(default_factory=list, description="Goodreads bookshelves, carried over as tags")


class GoodreadsPreviewResponse(BaseModel):
	rows: list[GoodreadsPreviewRowResponse] = Field(..., description="One entry per CSV row, in file order")


class GoodreadsConfirmItem(BaseModel):
	row_number: int = Field(..., description="Echoes the row reviewed in the preview")
	title: str = Field(..., min_length=1, max_length=500)
	main_author: str | None = Field(None, max_length=200)
	other_authors: list[str] = Field(default_factory=list)
	isbn: str | None = Field(None, max_length=20)
	publisher: str | None = Field(None, max_length=200)
	publication_year: int | None = None
	reading_status: ReadingStatus = ReadingStatus.TO_READ
	rating: int | None = Field(None, ge=1, le=5)
	review: str | None = None
	read_at: datetime | None = None
	tags: list[str] = Field(default_factory=list)
	is_intentional_duplicate: bool = False


class GoodreadsConfirmRequest(BaseModel):
	items: list[GoodreadsConfirmItem] = Field(..., min_length=1, max_length=5000)


class GoodreadsSkippedItemResponse(BaseModel):
	title: str = Field(..., description="Title of the item that was not created")
	reason: Literal["already_owned", "duplicate_in_import"] = Field(
		...,
		description="already_owned: the library already had this book. "
		"duplicate_in_import: the same book appeared twice in this CSV.",
	)
	row_number: int = Field(..., description="Echoes the item's row_number, to match it back to what was sent")


class GoodreadsConfirmResponse(BaseModel):
	created_book_ids: list[UUID] = Field(..., description="Owned books created")
	skipped: list[GoodreadsSkippedItemResponse] = Field(..., description="Items not created, with why")
	rated_count: int = Field(..., description="How many created books got a rating from My Rating")
	read_count: int = Field(..., description="How many created books got a BookRead entry from Date Read")
