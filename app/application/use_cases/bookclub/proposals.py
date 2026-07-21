import logging
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import BookClubCycle, BookClubProposal, BookClubVote
from app.domain.repositories import (
    BibliographicRecordRepository,
    BookClubCycleRepository,
    BookClubProposalRepository,
    BookClubVoteRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class ProposalWithVotes:
    proposal: BookClubProposal
    vote_count: int
    voted_by_me: bool


@dataclass
class ProposeBookInput:
    library_id: UUID
    proposed_by: UUID
    bibliographic_record_id: UUID
    note: str | None = None


class ProposeBookUseCase:
    def __init__(
        self,
        proposal_repo: BookClubProposalRepository,
        record_repo: BibliographicRecordRepository,
    ) -> None:
        self._proposal_repo = proposal_repo
        self._record_repo = record_repo

    async def execute(self, inp: ProposeBookInput) -> BookClubProposal:
        record = await self._record_repo.find_by_id(inp.bibliographic_record_id)
        if record is None:
            raise LookupError("Bibliographic record not found")
        if record.library_id != inp.library_id:
            raise PermissionError("Record does not belong to this library")
        saved = await self._proposal_repo.add(
            BookClubProposal(
                library_id=inp.library_id,
                bibliographic_record_id=inp.bibliographic_record_id,
                proposed_by=inp.proposed_by,
                note=inp.note,
            )
        )
        logger.info("Book club proposal %s added in library %s", saved.id, inp.library_id)
        return saved


class ListProposalsUseCase:
    def __init__(
        self, proposal_repo: BookClubProposalRepository, vote_repo: BookClubVoteRepository
    ) -> None:
        self._proposal_repo = proposal_repo
        self._vote_repo = vote_repo

    async def execute(self, library_id: UUID, user_id: UUID) -> list[ProposalWithVotes]:
        proposals = await self._proposal_repo.list_by_library(library_id)
        votes = await self._vote_repo.list_by_proposals([p.id for p in proposals])
        counts: dict[UUID, int] = {}
        mine: set[UUID] = set()
        for v in votes:
            counts[v.proposal_id] = counts.get(v.proposal_id, 0) + 1
            if v.user_id == user_id:
                mine.add(v.proposal_id)
        return [
            ProposalWithVotes(
                proposal=p,
                vote_count=counts.get(p.id, 0),
                voted_by_me=p.id in mine,
            )
            for p in proposals
        ]


class ToggleVoteUseCase:
    """Adds the caller's vote for a proposal, or removes it if already present.
    Returns True when the vote is now set, False when it was cleared."""

    def __init__(
        self, proposal_repo: BookClubProposalRepository, vote_repo: BookClubVoteRepository
    ) -> None:
        self._proposal_repo = proposal_repo
        self._vote_repo = vote_repo

    async def execute(self, proposal_id: UUID, library_id: UUID, user_id: UUID) -> bool:
        proposal = await self._proposal_repo.find_by_id(proposal_id)
        if proposal is None:
            raise LookupError("Proposal not found")
        if proposal.library_id != library_id:
            raise PermissionError("Proposal does not belong to this library")
        existing = await self._vote_repo.find_by_proposal_and_user(proposal_id, user_id)
        if existing is not None:
            await self._vote_repo.delete(existing)
            return False
        await self._vote_repo.add(BookClubVote(proposal_id=proposal_id, user_id=user_id))
        return True


class PromoteProposalUseCase:
    """Turns a proposal into an active reading cycle and clears the whole
    proposal pool (a new voting round starts empty)."""

    def __init__(
        self,
        proposal_repo: BookClubProposalRepository,
        cycle_repo: BookClubCycleRepository,
        record_repo: BibliographicRecordRepository,
    ) -> None:
        self._proposal_repo = proposal_repo
        self._cycle_repo = cycle_repo
        self._record_repo = record_repo

    async def execute(self, proposal_id: UUID, library_id: UUID, created_by: UUID) -> BookClubCycle:
        proposal = await self._proposal_repo.find_by_id(proposal_id)
        if proposal is None:
            raise LookupError("Proposal not found")
        if proposal.library_id != library_id:
            raise PermissionError("Proposal does not belong to this library")
        record = await self._record_repo.find_by_id(proposal.bibliographic_record_id)
        if record is None:
            raise LookupError("Bibliographic record not found")
        cycle = await self._cycle_repo.add(
            BookClubCycle(
                library_id=library_id,
                bibliographic_record_id=proposal.bibliographic_record_id,
                title=record.title,
                created_by=created_by,
            )
        )
        # Clearing proposals cascades to their votes (FK ON DELETE CASCADE).
        await self._proposal_repo.delete_all_by_library(library_id)
        logger.info("Proposal %s promoted to cycle %s in library %s", proposal_id, cycle.id, library_id)
        return cycle
