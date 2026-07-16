import logging
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.domain.entities import ReadingSession
from app.domain.repositories import OwnedBookRepository, ReadingSessionRepository

logger = logging.getLogger(__name__)


@dataclass
class LogReadingSessionInput:
    owned_book_id: UUID
    library_id: UUID
    user_id: UUID
    kids_mode_enabled: bool
    minutes: int | None = None
    pages: int | None = None
    session_date: date | None = None


class LogReadingSessionUseCase:
    """Child self-service: the caller always logs their own session — there
    is no "log on behalf of" path, matching the plan's coordination model
    (kids own their reading data, parents only view it)."""

    def __init__(self, book_repo: OwnedBookRepository, session_repo: ReadingSessionRepository) -> None:
        self._book_repo = book_repo
        self._session_repo = session_repo

    async def execute(self, input: LogReadingSessionInput) -> ReadingSession:
        if not input.kids_mode_enabled:
            raise PermissionError("Kids mode is not enabled for this library")
        book = await self._book_repo.find_by_id(input.owned_book_id)
        if not book:
            raise LookupError("Book not found")
        if book.library_id != input.library_id:
            raise PermissionError("Book does not belong to this library")

        session = ReadingSession(
            owned_book_id=input.owned_book_id,
            user_id=input.user_id,
            minutes=input.minutes,
            pages=input.pages,
        )
        if input.session_date is not None:
            session.session_date = input.session_date

        saved = await self._session_repo.add(session)
        logger.info("Reading session logged by user %s for book %s", input.user_id, input.owned_book_id)
        return saved


@dataclass
class ListReadingSessionsInput:
    target_user_id: UUID
    library_id: UUID
    requester_user_id: UUID
    requester_role: str
    kids_mode_enabled: bool


class ListReadingSessionsUseCase:
    """A child sees only their own sessions; a parent (admin/editor) can view
    any member's, for the read-only parent dashboard."""

    def __init__(self, session_repo: ReadingSessionRepository) -> None:
        self._session_repo = session_repo

    async def execute(self, input: ListReadingSessionsInput) -> list[ReadingSession]:
        if not input.kids_mode_enabled:
            raise PermissionError("Kids mode is not enabled for this library")
        is_self = input.target_user_id == input.requester_user_id
        is_parent = input.requester_role in ("admin", "editor")
        if not is_self and not is_parent:
            raise PermissionError("Cannot view another user's reading sessions")
        return await self._session_repo.list_by_user_and_library(input.target_user_id, input.library_id)
