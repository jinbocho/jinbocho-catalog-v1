from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.entities.book_club_cycle import BookClubCycleStatus
from app.domain.entities.book_club_participant import ParticipantStatus


class CycleCreate(BaseModel):
    bibliographic_record_id: UUID = Field(..., description="Record the club will read")
    title: str = Field(..., min_length=1, max_length=200, description="Cycle name or theme")
    owned_book_id: UUID | None = Field(
        None, description="Physical copy the club reads, when the library owns one"
    )
    reading_start: date | None = Field(None, description="Planned reading start date")
    reading_end: date | None = Field(None, description="Planned reading end date")


class CycleAdvance(BaseModel):
    target_status: BookClubCycleStatus = Field(..., description="Next status to move the cycle to")


class CycleResponse(BaseModel):
    id: UUID = Field(..., description="Cycle ID")
    library_id: UUID = Field(..., description="Owning library")
    bibliographic_record_id: UUID = Field(..., description="Record being read")
    owned_book_id: UUID | None = Field(None, description="Physical copy, if owned")
    title: str = Field(..., description="Cycle name or theme")
    status: BookClubCycleStatus = Field(..., description="Current cycle status")
    reading_start: date | None = Field(None, description="Planned reading start")
    reading_end: date | None = Field(None, description="Planned reading end")
    created_by: UUID = Field(..., description="Member who created the cycle")
    created_at: datetime = Field(..., description="When the cycle was created")

    model_config = ConfigDict(from_attributes=True)


class PostCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=8000, description="Discussion message")
    parent_post_id: UUID | None = Field(None, description="Reply target, for threading")
    is_spoiler: bool = Field(False, description="Hide behind a spoiler warning in the UI")


class PostResponse(BaseModel):
    id: UUID = Field(..., description="Post ID")
    cycle_id: UUID = Field(..., description="Cycle the post belongs to")
    user_id: UUID = Field(..., description="Author")
    body: str = Field(..., description="Discussion message")
    parent_post_id: UUID | None = Field(None, description="Reply target, if any")
    is_spoiler: bool = Field(..., description="Whether the post is marked as a spoiler")
    created_at: datetime = Field(..., description="When the post was created")

    model_config = ConfigDict(from_attributes=True)


class ProposalCreate(BaseModel):
    bibliographic_record_id: UUID = Field(..., description="Record proposed for the next cycle")
    note: str | None = Field(None, max_length=2000, description="Why you propose it")


class ProposalResponse(BaseModel):
    id: UUID = Field(..., description="Proposal ID")
    bibliographic_record_id: UUID = Field(..., description="Proposed record")
    proposed_by: UUID = Field(..., description="Member who proposed it")
    note: str | None = Field(None, description="Proposal note")
    created_at: datetime = Field(..., description="When it was proposed")
    vote_count: int = Field(..., description="Number of votes")
    voted_by_me: bool = Field(..., description="Whether the current member voted for it")


class VoteToggleResponse(BaseModel):
    voted: bool = Field(..., description="True if the vote is now set, False if it was cleared")


class ParticipantStatusUpdate(BaseModel):
    status: ParticipantStatus = Field(..., description="joined or finished")


class ParticipantResponse(BaseModel):
    id: UUID = Field(..., description="Participation ID")
    cycle_id: UUID = Field(..., description="Cycle")
    user_id: UUID = Field(..., description="Member")
    status: ParticipantStatus = Field(..., description="joined or finished")
    joined_at: datetime = Field(..., description="When the member joined")

    model_config = ConfigDict(from_attributes=True)


class MeetingCreate(BaseModel):
    scheduled_at: datetime = Field(..., description="Meeting date and time")
    note: str | None = Field(None, max_length=2000, description="Place or video-call link")


class MeetingResponse(BaseModel):
    id: UUID = Field(..., description="Meeting ID")
    cycle_id: UUID = Field(..., description="Cycle")
    scheduled_at: datetime = Field(..., description="Meeting date and time")
    note: str | None = Field(None, description="Place or link")
    created_by: UUID = Field(..., description="Member who scheduled it")
    created_at: datetime = Field(..., description="When it was scheduled")

    model_config = ConfigDict(from_attributes=True)


class QuestionsResponse(BaseModel):
    questions: list[str] = Field(..., description="AI discussion prompts; empty when AI is off")


class CycleRatingResponse(BaseModel):
    average: float | None = Field(None, description="Average member rating of the cycle's book")
    total: int = Field(..., description="Number of ratings")


class HistoryEntryResponse(BaseModel):
    cycle: CycleResponse = Field(..., description="The archived cycle")
    participant_count: int = Field(..., description="Members who took part")
    average_rating: float | None = Field(None, description="Group's average rating")
