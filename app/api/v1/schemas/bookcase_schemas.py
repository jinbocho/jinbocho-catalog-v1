from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BookcaseCreate(BaseModel):
	room_id: UUID = Field(..., description="Room ID")
	name: str = Field(..., description="Bookcase name")
	description: Optional[str] = Field(None, description="Bookcase description")
	type: Optional[str] = Field(None, description="Bookcase type (e.g., shelving, cabinet)")
	notes: Optional[str] = Field(None, description="Additional notes")
	image_url: Optional[str] = Field(None, description="Image URL")


class BookcaseUpdate(BaseModel):
	room_id: Optional[UUID] = Field(None, description="Room ID")
	name: Optional[str] = Field(None, description="Bookcase name")
	description: Optional[str] = Field(None, description="Bookcase description")
	type: Optional[str] = Field(None, description="Bookcase type")
	notes: Optional[str] = Field(None, description="Additional notes")
	image_url: Optional[str] = Field(None, description="Image URL")


class BookcaseResponse(BaseModel):
	id: UUID = Field(..., description="Bookcase ID")
	room_id: UUID = Field(..., description="Room ID")
	family_id: UUID = Field(..., description="Family ID")
	name: str = Field(..., description="Bookcase name")
	description: Optional[str] = Field(None, description="Bookcase description")
	type: Optional[str] = Field(None, description="Bookcase type")
	notes: Optional[str] = Field(None, description="Additional notes")
	image_url: Optional[str] = Field(None, description="Image URL")
	created_at: str = Field(..., description="Creation timestamp")
	updated_at: str = Field(..., description="Last update timestamp")

	class Config:
		from_attributes = True
