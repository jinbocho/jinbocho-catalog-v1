from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ShelfCreate(BaseModel):
	section_id: UUID = Field(..., description="Section ID")
	shelf_index: int = Field(..., description="Shelf index")
	notes: Optional[str] = Field(None, description="Notes")


class ShelfUpdate(BaseModel):
	section_id: Optional[UUID] = Field(None, description="Section ID")
	shelf_index: Optional[int] = Field(None, description="Shelf index")
	notes: Optional[str] = Field(None, description="Notes")


class ShelfResponse(BaseModel):
	id: UUID = Field(..., description="Shelf ID")
	section_id: UUID = Field(..., description="Section ID")
	shelf_index: int = Field(..., description="Shelf index")
	notes: Optional[str] = Field(None, description="Notes")
	created_at: str = Field(..., description="Creation timestamp")
	updated_at: str = Field(..., description="Last update timestamp")

	class Config:
		from_attributes = True
