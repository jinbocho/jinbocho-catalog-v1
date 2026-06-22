from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RoomCreate(BaseModel):
	name: str = Field(..., description="Name of the room")
	description: str | None = Field(None, description="Room description")

	class Config:
		json_schema_extra = {
			"example": {
				"name": "Living Room",
				"description": "Main bookcase in the living room"
			}
		}


class RoomUpdate(BaseModel):
	name: str | None = Field(None, description="Name of the room")
	description: str | None = Field(None, description="Room description")


class RoomResponse(BaseModel):
	id: UUID = Field(..., description="Room ID")
	family_id: UUID = Field(..., description="Family ID")
	name: str = Field(..., description="Name of the room")
	description: str | None = Field(None, description="Room description")
	created_at: datetime = Field(..., description="Creation timestamp")
	updated_at: datetime = Field(..., description="Last update timestamp")

	class Config:
		from_attributes = True
