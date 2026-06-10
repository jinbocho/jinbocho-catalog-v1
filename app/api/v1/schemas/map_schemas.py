from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BookOnShelfResponse(BaseModel):
	id: UUID = Field(..., description="Book ID")
	title: Optional[str] = Field(None, description="Book title")
	main_author: Optional[str] = Field(None, description="Main author")
	reading_status: str = Field(..., description="Reading status")


class ShelfMapResponse(BaseModel):
	shelf_id: UUID = Field(..., description="Shelf ID")
	shelf_index: int = Field(..., description="Shelf index")
	books: list[BookOnShelfResponse] = Field(..., description="Books on this shelf")


class SectionMapResponse(BaseModel):
	section_id: UUID = Field(..., description="Section ID")
	section_index: int = Field(..., description="Section index")
	label: Optional[str] = Field(None, description="Custom section label")
	shelves: list[ShelfMapResponse] = Field(..., description="Shelves in this section")


class BookcaseMapResponse(BaseModel):
	bookcase_id: UUID = Field(..., description="Bookcase ID")
	bookcase_name: str = Field(..., description="Bookcase name")
	sections: list[SectionMapResponse] = Field(..., description="Sections in this bookcase")
