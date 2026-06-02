from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SectionCreate(BaseModel):
	bookcase_id: UUID = Field(..., description="Bookcase ID")
	section_index: int = Field(..., description="Section index")
	label: Optional[str] = Field(None, description="Section label")


class SectionUpdate(BaseModel):
	bookcase_id: Optional[UUID] = Field(None, description="Bookcase ID")
	section_index: Optional[int] = Field(None, description="Section index")
	label: Optional[str] = Field(None, description="Section label")


class SectionResponse(BaseModel):
	id: UUID = Field(..., description="Section ID")
	bookcase_id: UUID = Field(..., description="Bookcase ID")
	section_index: int = Field(..., description="Section index")
	label: Optional[str] = Field(None, description="Section label")
	created_at: str = Field(..., description="Creation timestamp")
	updated_at: str = Field(..., description="Last update timestamp")

	class Config:
		from_attributes = True
