import logging
from uuid import UUID

from app.domain.entities import BookClubParticipant
from app.domain.entities.book_club_participant import ParticipantStatus
from app.domain.repositories import BookClubCycleRepository, BookClubParticipantRepository

logger = logging.getLogger(__name__)


async def _load_cycle_in_library(
    cycle_repo: BookClubCycleRepository, cycle_id: UUID, library_id: UUID
) -> None:
    cycle = await cycle_repo.find_by_id(cycle_id)
    if cycle is None:
        raise LookupError("Cycle not found")
    if cycle.library_id != library_id:
        raise PermissionError("Cycle does not belong to this library")


class JoinCycleUseCase:
    def __init__(
        self,
        cycle_repo: BookClubCycleRepository,
        participant_repo: BookClubParticipantRepository,
    ) -> None:
        self._cycle_repo = cycle_repo
        self._participant_repo = participant_repo

    async def execute(self, cycle_id: UUID, library_id: UUID, user_id: UUID) -> BookClubParticipant:
        await _load_cycle_in_library(self._cycle_repo, cycle_id, library_id)
        existing = await self._participant_repo.find_by_cycle_and_user(cycle_id, user_id)
        if existing is not None:
            return existing
        saved = await self._participant_repo.add(
            BookClubParticipant(cycle_id=cycle_id, user_id=user_id)
        )
        logger.info("User %s joined cycle %s", user_id, cycle_id)
        return saved


class SetParticipantStatusUseCase:
    def __init__(
        self,
        cycle_repo: BookClubCycleRepository,
        participant_repo: BookClubParticipantRepository,
    ) -> None:
        self._cycle_repo = cycle_repo
        self._participant_repo = participant_repo

    async def execute(
        self, cycle_id: UUID, library_id: UUID, user_id: UUID, status: ParticipantStatus
    ) -> BookClubParticipant:
        await _load_cycle_in_library(self._cycle_repo, cycle_id, library_id)
        participant = await self._participant_repo.find_by_cycle_and_user(cycle_id, user_id)
        if participant is None:
            raise LookupError("You have not joined this cycle")
        participant.status = status
        return await self._participant_repo.save(participant)


class ListParticipantsUseCase:
    def __init__(
        self,
        cycle_repo: BookClubCycleRepository,
        participant_repo: BookClubParticipantRepository,
    ) -> None:
        self._cycle_repo = cycle_repo
        self._participant_repo = participant_repo

    async def execute(self, cycle_id: UUID, library_id: UUID) -> list[BookClubParticipant]:
        await _load_cycle_in_library(self._cycle_repo, cycle_id, library_id)
        return await self._participant_repo.list_by_cycle(cycle_id)
