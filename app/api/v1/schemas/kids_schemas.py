from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReadingSessionCreate(BaseModel):
	owned_book_id: UUID = Field(..., description="Book the session was logged against")
	minutes: int | None = Field(None, ge=1, description="Minutes spent reading")
	pages: int | None = Field(None, ge=1, description="Pages read")
	session_date: date | None = Field(None, description="Defaults to today if omitted")

	@model_validator(mode="after")
	def _require_minutes_or_pages(self) -> "ReadingSessionCreate":
		if self.minutes is None and self.pages is None:
			raise ValueError("Provide at least one of minutes or pages")
		return self


class ReadingSessionResponse(BaseModel):
	id: UUID = Field(..., description="Reading session ID")
	owned_book_id: UUID = Field(..., description="Book copy ID")
	user_id: UUID = Field(..., description="Child who logged the session")
	minutes: int | None = Field(None, description="Minutes spent reading")
	pages: int | None = Field(None, description="Pages read")
	session_date: date = Field(..., description="Date the session took place")
	created_at: datetime = Field(..., description="When the session was logged")

	model_config = ConfigDict(from_attributes=True)


class QuizGenerateRequest(BaseModel):
	num_questions: int = Field(5, ge=1, le=10, description="How many AI questions to generate, if none exist yet")
	extra_context: str | None = Field(
		None,
		max_length=2000,
		description="Optional free text to guide the AI questions — can be a plot summary, where the "
		"reader is in the book, or what to focus on. Providing this always asks the AI for more "
		"questions (bypassing the get-or-generate default) and appends them.",
	)


class QuizQuestionCreate(BaseModel):
	prompt: str = Field(..., min_length=1, max_length=1000)
	choices: list[str] = Field(..., min_length=2, max_length=6)
	correct_index: int = Field(..., ge=0, description="Index into choices")

	@model_validator(mode="after")
	def _validate_correct_index(self) -> "QuizQuestionCreate":
		if self.correct_index >= len(self.choices):
			raise ValueError("correct_index is out of range for the given choices")
		return self


class QuizQuestionResponse(BaseModel):
	"""Sanitized — no correct_index, so a child taking the quiz can't read the
	answer off the network response before submitting."""

	id: UUID
	owned_book_id: UUID
	prompt: str
	choices: list[str]
	source: str

	model_config = ConfigDict(from_attributes=True)


class QuizQuestionAuthorResponse(QuizQuestionResponse):
	"""Returned only to the parent who just authored the question — includes
	correct_index so the UI can show what was saved."""

	correct_index: int


class QuizSubmitRequest(BaseModel):
	answers: dict[UUID, int] = Field(..., description="question_id -> chosen choice index", min_length=1)


class QuizAttemptResponse(BaseModel):
	id: UUID
	owned_book_id: UUID
	user_id: UUID
	score: int
	total: int
	passed: bool
	created_at: datetime

	model_config = ConfigDict(from_attributes=True)


class QuizAnswerReviewResponse(BaseModel):
	"""One answered question, for the parent-dashboard "view answers" modal —
	only ever returned after the attempt is already submitted, so revealing
	correct_index here is not the pre-answer leak QuizQuestionResponse guards against."""

	question_id: UUID
	prompt: str
	choices: list[str]
	correct_index: int
	selected_index: int
	is_correct: bool


class QuizAttemptDetailResponse(BaseModel):
	id: UUID
	owned_book_id: UUID
	user_id: UUID
	score: int
	total: int
	passed: bool
	created_at: datetime
	answers: list[QuizAnswerReviewResponse]
