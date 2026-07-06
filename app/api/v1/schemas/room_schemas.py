from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RoomCreate(BaseModel):
	name: str = Field(..., description="Name of the room")
	description: str | None = Field(None, description="Room description")

	model_config = ConfigDict(
		json_schema_extra={
			"example": {
				"name": "Living Room",
				"description": "Main bookcase in the living room"
			}
		}
	)


class RoomUpdate(BaseModel):
	name: str | None = Field(None, description="Name of the room")
	description: str | None = Field(None, description="Room description")


class RoomResponse(BaseModel):
	id: UUID = Field(..., description="Room ID")
	library_id: UUID = Field(..., description="Library ID")
	name: str = Field(..., description="Name of the room")
	description: str | None = Field(None, description="Room description")
	created_at: datetime = Field(..., description="Creation timestamp")
	updated_at: datetime = Field(..., description="Last update timestamp")

	model_config = ConfigDict(from_attributes=True)
