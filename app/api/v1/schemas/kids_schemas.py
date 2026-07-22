from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReadingSessionCreate(BaseModel):
	owned_book_id: UUID = Field(..., description="Book the session was logged against")
	minutes: int | None = Field(None, ge=1, description="Minutes spent reading")
	pages: int | None = Field(None, ge=1, description="Pages read")
	session_date: date | None = Field(None, description="Defaults to today if omitted")
	target_user_id: UUID | None = Field(
		None, description="Child this session is for — omit to log your own (self-service). "
		"Required for mode='together', where a parent logs on the child's behalf (KID-02)."
	)
	mode: str = Field(
		"independent",
		description="'independent' (child reading alone) or 'together' (parent reading aloud with a 0-5 child)",
	)

	@model_validator(mode="after")
	def _require_minutes_or_pages(self) -> "ReadingSessionCreate":
		if self.minutes is None and self.pages is None:
			raise ValueError("Provide at least one of minutes or pages")
		return self


class ReadingSessionResponse(BaseModel):
	id: UUID = Field(..., description="Reading session ID")
	owned_book_id: UUID = Field(..., description="Book copy ID")
	user_id: UUID = Field(..., description="Child the session was logged for")
	minutes: int | None = Field(None, description="Minutes spent reading")
	pages: int | None = Field(None, description="Pages read")
	session_date: date = Field(..., description="Date the session took place")
	mode: str = Field(..., description="'independent' or 'together'")
	logged_by_user_id: UUID | None = Field(None, description="Parent who logged a 'together' session, if any")
	created_at: datetime = Field(..., description="When the session was logged")

	model_config = ConfigDict(from_attributes=True)


class FinishSharedReadingRequest(BaseModel):
	target_user_id: UUID = Field(..., description="The 0-5 child whose shared book is being marked finished")


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


class DiscussionQuestionsResponse(BaseModel):
	"""KID-04 dinner-table conversation starters — no right answer, so unlike
	QuizQuestionResponse there's nothing to sanitize out."""

	questions: list[str]


class JournalEntryCreate(BaseModel):
	owned_book_id: UUID = Field(..., description="Book the entry is about")
	text: str = Field(..., min_length=1, max_length=4000, description="Free text, emoji+sentence, or retelling")
	prompt_kind: str = Field("free", description="'free', 'retelling', or 'creative'")
	emoji: str | None = Field(None, max_length=8, description="For the 6-8 emoji+sentence style")
	session_id: UUID | None = Field(None, description="Reading session this entry follows, if any")


class JournalEntryResponse(BaseModel):
	id: UUID = Field(..., description="Journal entry ID")
	owned_book_id: UUID = Field(..., description="Book copy ID")
	user_id: UUID = Field(..., description="Child who wrote the entry")
	text: str = Field(..., description="Entry text")
	prompt_kind: str = Field(..., description="'free', 'retelling', or 'creative'")
	emoji: str | None = Field(None, description="Emoji, if any")
	session_id: UUID | None = Field(None, description="Linked reading session, if any")
	created_at: datetime = Field(..., description="When the entry was written")

	model_config = ConfigDict(from_attributes=True)


class ReadingPathCreate(BaseModel):
	title: str = Field(..., min_length=1, max_length=255, description="Path title")
	book_ids: list[UUID] = Field(..., min_length=1, description="Ordered list of owned book IDs")
	description: str | None = Field(None, max_length=2000, description="Why these books, in what order")
	target_band: str | None = Field(None, description="'shared', 'emerging', 'fluent', or 'teen'")


class ReadingPathResponse(BaseModel):
	id: UUID = Field(..., description="Reading path ID")
	library_id: UUID = Field(..., description="Library this path belongs to")
	title: str = Field(..., description="Path title")
	description: str | None = Field(None, description="Description")
	book_ids: list[UUID] = Field(..., description="Ordered list of owned book IDs")
	target_band: str | None = Field(None, description="Target age band, if any")
	source: str = Field(..., description="'manual' or 'ai'")
	created_by: UUID | None = Field(None, description="Who created this path")
	created_at: datetime = Field(..., description="When the path was created")

	model_config = ConfigDict(from_attributes=True)


class MysteryPickCreate(BaseModel):
	owned_book_id: UUID = Field(..., description="The book being proposed")
	child_user_id: UUID = Field(..., description="The child this mystery pick is for")


class MysteryPickResponse(BaseModel):
	id: UUID = Field(..., description="Mystery pick ID")
	# None while status='proposed' and the viewer is the target child — the
	# whole point is the identity stays hidden until they accept. Always
	# populated for the parent who created it, and for either side once
	# accepted. Sanitization happens at the endpoint, not here.
	owned_book_id: UUID | None = Field(None, description="Hidden from the child until accepted")
	child_user_id: UUID = Field(..., description="The child this mystery pick is for")
	hint_text: str = Field(..., description="Masked hint — never reveals the title/author outright")
	status: str = Field(..., description="'proposed' or 'accepted'")
	created_at: datetime = Field(..., description="When the pick was proposed")


class FamilyChallengeCreate(BaseModel):
	title: str = Field(..., min_length=1, max_length=255, description="Challenge title")
	metric: str = Field(..., description="'minutes', 'sessions', or 'books'")
	target: int = Field(..., gt=0, description="Shared target the whole family works toward")
	starts_on: date = Field(..., description="Challenge start date")
	ends_on: date = Field(..., description="Challenge end date")


class FamilyChallengeResponse(BaseModel):
	id: UUID = Field(..., description="Family challenge ID")
	library_id: UUID = Field(..., description="Library this challenge belongs to")
	title: str = Field(..., description="Challenge title")
	metric: str = Field(..., description="'minutes', 'sessions', or 'books'")
	target: int = Field(..., description="Shared target")
	starts_on: date = Field(..., description="Challenge start date")
	ends_on: date = Field(..., description="Challenge end date")
	created_by: UUID | None = Field(None, description="Who created this challenge")
	created_at: datetime = Field(..., description="When the challenge was created")

	model_config = ConfigDict(from_attributes=True)


class FamilyChallengeProgressResponse(BaseModel):
	challenge: FamilyChallengeResponse
	# Deliberately a single cooperative number, never broken down per member —
	# see FamilyChallenge's docstring. No leaderboard, ever.
	current: int = Field(..., description="Current progress toward the shared target")
