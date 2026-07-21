import logging
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.domain.entities import BookClubCycle
from app.domain.entities.book_club_cycle import BookClubCycleStatus
from app.domain.repositories import (
    BibliographicRecordRepository,
    BookClubCycleRepository,
    OwnedBookRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class CreateCycleInput:
    library_id: UUID
    created_by: UUID
    bibliographic_record_id: UUID
    title: str
    owned_book_id: UUID | None = None
    reading_start: date | None = None
    reading_end: date | None = None


class CreateCycleUseCase:
    def __init__(
        self,
        cycle_repo: BookClubCycleRepository,
        record_repo: BibliographicRecordRepository,
        book_repo: OwnedBookRepository,
    ) -> None:
        self._cycle_repo = cycle_repo
        self._record_repo = record_repo
        self._book_repo = book_repo

    async def execute(self, inp: CreateCycleInput) -> BookClubCycle:
        record = await self._record_repo.find_by_id(inp.bibliographic_record_id)
        if record is None:
            raise LookupError("Bibliographic record not found")
        if record.library_id != inp.library_id:
            raise PermissionError("Record does not belong to this library")
        if inp.owned_book_id is not None:
            book = await self._book_repo.find_by_id(inp.owned_book_id)
            if book is None:
                raise LookupError("Book not found")
            if book.library_id != inp.library_id:
                raise PermissionError("Book does not belong to this library")
        saved = await self._cycle_repo.add(
            BookClubCycle(
                library_id=inp.library_id,
                bibliographic_record_id=inp.bibliographic_record_id,
                title=inp.title,
                created_by=inp.created_by,
                owned_book_id=inp.owned_book_id,
                reading_start=inp.reading_start,
                reading_end=inp.reading_end,
            )
        )
        logger.info("Book club cycle %s created in library %s", saved.id, inp.library_id)
        return saved


class ListCyclesUseCase:
    def __init__(self, cycle_repo: BookClubCycleRepository) -> None:
        self._cycle_repo = cycle_repo

    async def execute(self, library_id: UUID) -> list[BookClubCycle]:
        return await self._cycle_repo.list_by_library(library_id)


class GetCycleUseCase:
    def __init__(self, cycle_repo: BookClubCycleRepository) -> None:
        self._cycle_repo = cycle_repo

    async def execute(self, cycle_id: UUID, library_id: UUID) -> BookClubCycle:
        cycle = await self._cycle_repo.find_by_id(cycle_id)
        if cycle is None:
            raise LookupError("Cycle not found")
        if cycle.library_id != library_id:
            raise PermissionError("Cycle does not belong to this library")
        return cycle


@dataclass
class AdvanceCycleStatusInput:
    cycle_id: UUID
    library_id: UUID
    target_status: BookClubCycleStatus


class AdvanceCycleStatusUseCase:
    def __init__(self, cycle_repo: BookClubCycleRepository) -> None:
        self._cycle_repo = cycle_repo

    async def execute(self, inp: AdvanceCycleStatusInput) -> BookClubCycle:
        cycle = await self._cycle_repo.find_by_id(inp.cycle_id)
        if cycle is None:
            raise LookupError("Cycle not found")
        if cycle.library_id != inp.library_id:
            raise PermissionError("Cycle does not belong to this library")
        if not cycle.can_transition_to(inp.target_status):
            raise ValueError(f"Cannot move cycle from {cycle.status} to {inp.target_status}")
        cycle.status = inp.target_status
        saved = await self._cycle_repo.save(cycle)
        logger.info("Book club cycle %s advanced to %s", cycle.id, inp.target_status)
        return saved


class ArchiveCycleUseCase:
    def __init__(self, cycle_repo: BookClubCycleRepository) -> None:
        self._cycle_repo = cycle_repo

    async def execute(self, cycle_id: UUID, library_id: UUID) -> BookClubCycle:
        cycle = await self._cycle_repo.find_by_id(cycle_id)
        if cycle is None:
            raise LookupError("Cycle not found")
        if cycle.library_id != library_id:
            raise PermissionError("Cycle does not belong to this library")
        if not cycle.can_transition_to(BookClubCycleStatus.ARCHIVED):
            raise ValueError(f"Cannot archive a cycle in {cycle.status} status")
        cycle.status = BookClubCycleStatus.ARCHIVED
        saved = await self._cycle_repo.save(cycle)
        logger.info("Book club cycle %s archived in library %s", cycle.id, library_id)
        return saved
