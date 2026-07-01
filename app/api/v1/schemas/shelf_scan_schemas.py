from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# ~6MB of image after base64 expansion — the FE downscales shelf photos to
# ~1500px so real payloads stay far below this; the cap only guards abuse.
_MAX_IMAGE_BASE64_LENGTH = 8_000_000


class ShelfScanRequest(BaseModel):
	shelf_id: UUID = Field(..., description="Shelf the photographed books will be assigned to")
	image_base64: str = Field(..., max_length=_MAX_IMAGE_BASE64_LENGTH, description="Shelf photo, base64-encoded")
	media_type: Literal["image/jpeg", "image/png", "image/webp"] = Field(
		default="image/jpeg", description="MIME type of the encoded photo"
	)


class ShelfScanCandidateResponse(BaseModel):
	spine_title: str = Field(..., description="Title as transcribed from the spine")
	spine_author: str | None = Field(None, description="Author as transcribed from the spine, if legible")
	position: int = Field(..., description="Left-to-right order on the photographed shelf")
	status: Literal["matched", "uncertain", "not_found"] = Field(
		..., description="Confidence of the metadata provider match"
	)
	already_owned: bool = Field(..., description="Whether the family already owns this title")
	metadata: dict[str, Any] | None = Field(None, description="Best provider match metadata, if any")


class ShelfScanResponse(BaseModel):
	available: bool = Field(..., description="False when the vision LLM is disabled or unreachable")
	reason: str = Field(default="ok", description="ok | disabled | unsupported | error — why unavailable")
	candidates: list[ShelfScanCandidateResponse] = Field(..., description="One entry per legible spine")


class ShelfScanConfirmItem(BaseModel):
	title: str = Field(..., min_length=1, max_length=500)
	main_author: str | None = Field(None, max_length=200)
	isbn: str | None = Field(None, max_length=20)
	publisher: str | None = Field(None, max_length=200)
	publication_year: int | None = None
	language: str | None = Field(None, max_length=10)
	genre: str | None = Field(None, max_length=100)
	cover_url: str | None = Field(None, max_length=500)
	position: int = Field(default=0, ge=0, description="Left-to-right order of the spine on the shelf")
	is_intentional_duplicate: bool = False


class ShelfScanConfirmRequest(BaseModel):
	shelf_id: UUID = Field(..., description="Shelf the books will be positioned on")
	items: list[ShelfScanConfirmItem] = Field(..., min_length=1, max_length=100)


class ShelfScanConfirmResponse(BaseModel):
	created_book_ids: list[UUID] = Field(..., description="Owned books created, in shelf order")
	skipped_titles: list[str] = Field(..., description="Items skipped because already owned")


class ShelfAuditRequest(BaseModel):
	shelf_id: UUID = Field(..., description="Shelf being audited")
	image_base64: str = Field(..., max_length=_MAX_IMAGE_BASE64_LENGTH, description="Shelf photo, base64-encoded")
	media_type: Literal["image/jpeg", "image/png", "image/webp"] = Field(default="image/jpeg")


class AuditBookResponse(BaseModel):
	owned_book_id: UUID
	title: str
	main_author: str | None = None


class AuditUnexpectedResponse(BaseModel):
	title: str
	author: str | None = None
	position: int


class ShelfAuditResponse(BaseModel):
	available: bool = Field(..., description="False when the vision LLM is disabled or unreachable")
	reason: str = Field(default="ok", description="ok | disabled | unsupported | error — why unavailable")
	present: list[AuditBookResponse] = Field(..., description="Catalogued here and seen in the photo")
	missing: list[AuditBookResponse] = Field(..., description="Catalogued here but not seen — moved/lent/lost")
	unexpected: list[AuditUnexpectedResponse] = Field(..., description="Seen in the photo but not catalogued here")
