from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BookcaseCreate(BaseModel):
	room_id: UUID = Field(..., description="Room ID")
	name: str = Field(..., description="Bookcase name")
	description: str | None = Field(None, description="Bookcase description")
	type: str | None = Field(None, description="Bookcase type (e.g., shelving, cabinet)")
	notes: str | None = Field(None, description="Additional notes")
	image_url: str | None = Field(None, description="Image URL")


class BookcaseUpdate(BaseModel):
	room_id: UUID | None = Field(None, description="Room ID")
	name: str | None = Field(None, description="Bookcase name")
	description: str | None = Field(None, description="Bookcase description")
	type: str | None = Field(None, description="Bookcase type")
	notes: str | None = Field(None, description="Additional notes")
	image_url: str | None = Field(None, description="Image URL")


class BookcaseResponse(BaseModel):
	id: UUID = Field(..., description="Bookcase ID")
	room_id: UUID = Field(..., description="Room ID")
	family_id: UUID = Field(..., description="Family ID")
	name: str = Field(..., description="Bookcase name")
	description: str | None = Field(None, description="Bookcase description")
	type: str | None = Field(None, description="Bookcase type")
	notes: str | None = Field(None, description="Additional notes")
	image_url: str | None = Field(None, description="Image URL")
	created_at: datetime = Field(..., description="Creation timestamp")
	updated_at: datetime = Field(..., description="Last update timestamp")

	class Config:
		from_attributes = True
