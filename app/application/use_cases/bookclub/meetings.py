import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.entities import BookClubMeeting
from app.domain.repositories import BookClubCycleRepository, BookClubMeetingRepository

logger = logging.getLogger(__name__)


async def _load_cycle_in_library(
    cycle_repo: BookClubCycleRepository, cycle_id: UUID, library_id: UUID
) -> None:
    cycle = await cycle_repo.find_by_id(cycle_id)
    if cycle is None:
        raise LookupError("Cycle not found")
    if cycle.library_id != library_id:
        raise PermissionError("Cycle does not belong to this library")


@dataclass
class ScheduleMeetingInput:
    cycle_id: UUID
    library_id: UUID
    created_by: UUID
    scheduled_at: datetime
    note: str | None = None


class ScheduleMeetingUseCase:
    def __init__(
        self, cycle_repo: BookClubCycleRepository, meeting_repo: BookClubMeetingRepository
    ) -> None:
        self._cycle_repo = cycle_repo
        self._meeting_repo = meeting_repo

    async def execute(self, inp: ScheduleMeetingInput) -> BookClubMeeting:
        await _load_cycle_in_library(self._cycle_repo, inp.cycle_id, inp.library_id)
        saved = await self._meeting_repo.add(
            BookClubMeeting(
                cycle_id=inp.cycle_id,
                scheduled_at=inp.scheduled_at,
                created_by=inp.created_by,
                note=inp.note,
            )
        )
        logger.info("Meeting %s scheduled for cycle %s", saved.id, inp.cycle_id)
        return saved


class ListMeetingsUseCase:
    def __init__(
        self, cycle_repo: BookClubCycleRepository, meeting_repo: BookClubMeetingRepository
    ) -> None:
        self._cycle_repo = cycle_repo
        self._meeting_repo = meeting_repo

    async def execute(self, cycle_id: UUID, library_id: UUID) -> list[BookClubMeeting]:
        await _load_cycle_in_library(self._cycle_repo, cycle_id, library_id)
        return await self._meeting_repo.list_by_cycle(cycle_id)


class DeleteMeetingUseCase:
    def __init__(
        self, cycle_repo: BookClubCycleRepository, meeting_repo: BookClubMeetingRepository
    ) -> None:
        self._cycle_repo = cycle_repo
        self._meeting_repo = meeting_repo

    async def execute(self, meeting_id: UUID, library_id: UUID) -> None:
        meeting = await self._meeting_repo.find_by_id(meeting_id)
        if meeting is None:
            raise LookupError("Meeting not found")
        await _load_cycle_in_library(self._cycle_repo, meeting.cycle_id, library_id)
        await self._meeting_repo.delete(meeting)
        logger.info("Meeting %s deleted from cycle %s", meeting_id, meeting.cycle_id)
