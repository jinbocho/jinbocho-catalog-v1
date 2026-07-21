from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import BookClubCycle, LibraryRatingStats
from app.domain.entities.book_club_cycle import BookClubCycleStatus
from app.domain.repositories import (
    BookClubCycleRepository,
    BookClubParticipantRepository,
    BookRatingRepository,
    OwnedBookRepository,
)


@dataclass
class CycleRatingSummary:
    average: float | None
    total: int


@dataclass
class SharedHistoryEntry:
    cycle: BookClubCycle
    participant_count: int
    average_rating: float | None


class GetCycleRatingSummaryUseCase:
    """Aggregate of members' ratings on the cycle's book. Reuses BookRating on
    the owned copy — no separate club rating (see ADR-013)."""

    def __init__(
        self, cycle_repo: BookClubCycleRepository, rating_repo: BookRatingRepository
    ) -> None:
        self._cycle_repo = cycle_repo
        self._rating_repo = rating_repo

    async def execute(self, cycle_id: UUID, library_id: UUID) -> CycleRatingSummary:
        cycle = await self._cycle_repo.find_by_id(cycle_id)
        if cycle is None:
            raise LookupError("Cycle not found")
        if cycle.library_id != library_id:
            raise PermissionError("Cycle does not belong to this library")
        if cycle.owned_book_id is None:
            return CycleRatingSummary(average=None, total=0)
        ratings = await self._rating_repo.list_by_book(cycle.owned_book_id)
        stats = LibraryRatingStats.from_ratings(cycle.owned_book_id, ratings)
        return CycleRatingSummary(average=stats.average, total=stats.total)


class GetSharedHistoryUseCase:
    """Archived cycles with participant counts and the group's average rating —
    the club's shared reading history (CLUB-03)."""

    def __init__(
        self,
        cycle_repo: BookClubCycleRepository,
        participant_repo: BookClubParticipantRepository,
        rating_repo: BookRatingRepository,
        book_repo: OwnedBookRepository,
    ) -> None:
        self._cycle_repo = cycle_repo
        self._participant_repo = participant_repo
        self._rating_repo = rating_repo
        self._book_repo = book_repo

    async def execute(self, library_id: UUID) -> list[SharedHistoryEntry]:
        cycles = await self._cycle_repo.list_by_library(library_id)
        archived = [c for c in cycles if c.status is BookClubCycleStatus.ARCHIVED]
        entries: list[SharedHistoryEntry] = []
        for cycle in archived:
            participants = await self._participant_repo.list_by_cycle(cycle.id)
            average: float | None = None
            if cycle.owned_book_id is not None:
                ratings = await self._rating_repo.list_by_book(cycle.owned_book_id)
                stats = LibraryRatingStats.from_ratings(cycle.owned_book_id, ratings)
                average = stats.average
            entries.append(
                SharedHistoryEntry(
                    cycle=cycle,
                    participant_count=len(participants),
                    average_rating=average,
                )
            )
        return entries
