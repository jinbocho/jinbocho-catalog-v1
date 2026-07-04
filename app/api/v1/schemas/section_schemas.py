from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SectionCreate(BaseModel):
	bookcase_id: UUID = Field(..., description="Bookcase ID")
	section_index: int = Field(..., description="Section index")
	label: str | None = Field(None, description="Section label")


class SectionUpdate(BaseModel):
	bookcase_id: UUID | None = Field(None, description="Bookcase ID")
	section_index: int | None = Field(None, description="Section index")
	label: str | None = Field(None, description="Section label")


class SectionResponse(BaseModel):
	id: UUID = Field(..., description="Section ID")
	bookcase_id: UUID = Field(..., description="Bookcase ID")
	section_index: int = Field(..., description="Section index")
	label: str | None = Field(None, description="Section label")
	created_at: datetime = Field(..., description="Creation timestamp")
	updated_at: datetime = Field(..., description="Last update timestamp")

	model_config = ConfigDict(from_attributes=True)
