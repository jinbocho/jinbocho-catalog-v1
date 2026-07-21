import logging
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.domain.entities import ReadingSession, ReadingSessionMode
from app.domain.repositories import OwnedBookRepository, ReadingSessionRepository

logger = logging.getLogger(__name__)


@dataclass
class LogReadingSessionInput:
    owned_book_id: UUID
    library_id: UUID
    # Whose reading session this is (the child) — distinct from the requester
    # for KID-02 "together" sessions, where a parent logs on the child's behalf.
    target_user_id: UUID
    requester_user_id: UUID
    requester_role: str
    kids_mode_enabled: bool
    minutes: int | None = None
    pages: int | None = None
    session_date: date | None = None
    mode: ReadingSessionMode = ReadingSessionMode.INDEPENDENT


class LogReadingSessionUseCase:
    """Two paths: a child logging their own independent session (self-service,
    the original behavior), or a parent logging a "together" session on a
    0-5 child's behalf (KID-02) — never a parent claiming an independent
    session for someone else, which would misrepresent the child's own
    reading data."""

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

        is_parent = input.requester_role in ("admin", "editor")
        if input.mode == ReadingSessionMode.TOGETHER:
            if not is_parent:
                raise PermissionError("Only a parent can log a shared reading session")
            logged_by_user_id = input.requester_user_id
        else:
            if input.target_user_id != input.requester_user_id:
                raise PermissionError("Can only log your own independent reading session")
            logged_by_user_id = None

        session = ReadingSession(
            owned_book_id=input.owned_book_id,
            user_id=input.target_user_id,
            minutes=input.minutes,
            pages=input.pages,
            mode=input.mode,
            logged_by_user_id=logged_by_user_id,
        )
        if input.session_date is not None:
            session.session_date = input.session_date

        saved = await self._session_repo.add(session)
        logger.info(
            "Reading session (%s) logged for user %s on book %s by %s",
            input.mode.value, input.target_user_id, input.owned_book_id, input.requester_user_id,
        )
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
