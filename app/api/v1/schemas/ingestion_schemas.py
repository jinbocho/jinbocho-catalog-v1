from typing import Any, Optional

from pydantic import BaseModel, Field


class IsbnLookupResponse(BaseModel):
	source: str = Field(..., description="Source of metadata (google_books, open_library)")
	metadata: dict[str, Any] = Field(..., description="Book metadata")
	cached: bool = Field(..., description="Whether result was cached")


class BulkLookupRequest(BaseModel):
	isbns: list[str] = Field(
		...,
		min_length=1,
		max_length=100,
		description="List of ISBN codes to lookup",
	)
