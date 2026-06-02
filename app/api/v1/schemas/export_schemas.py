from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ExportedBookResponse(BaseModel):
	id: UUID = Field(..., description="Book ID")
	title: Optional[str] = Field(None, description="Book title")
	main_author: Optional[str] = Field(None, description="Main author")
	isbn: Optional[str] = Field(None, description="ISBN")
	reading_status: str = Field(..., description="Reading status")
	shelf_id: Optional[UUID] = Field(None, description="Current shelf ID")
