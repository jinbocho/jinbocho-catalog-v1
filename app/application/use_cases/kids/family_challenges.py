import logging
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.domain.entities import ChallengeMetric, FamilyChallenge
from app.domain.repositories import BookReadRepository, FamilyChallengeRepository, ReadingSessionRepository

logger = logging.getLogger(__name__)


@dataclass
class CreateFamilyChallengeInput:
    library_id: UUID
    created_by: UUID
    kids_mode_enabled: bool
    title: str
    metric: ChallengeMetric
    target: int
    starts_on: date
    ends_on: date


class CreateFamilyChallengeUseCase:
    """Parent-only (require_parent enforced at the endpoint)."""

    def __init__(self, challenge_repo: FamilyChallengeRepository) -> None:
        self._challenge_repo = challenge_repo

    async def execute(self, input: CreateFamilyChallengeInput) -> FamilyChallenge:
        if not input.kids_mode_enabled:
            raise PermissionError("Kids mode is not enabled for this library")
        if input.target <= 0:
            raise ValueError("Target must be positive")
        if input.ends_on < input.starts_on:
            raise ValueError("ends_on must not be before starts_on")

        challenge = FamilyChallenge(
            library_id=input.library_id,
            title=input.title,
            metric=input.metric,
            target=input.target,
            starts_on=input.starts_on,
            ends_on=input.ends_on,
            created_by=input.created_by,
        )
        saved = await self._challenge_repo.add(challenge)
        logger.info("Family challenge %s created in library %s", saved.id, input.library_id)
        return saved


@dataclass
class ListFamilyChallengesInput:
    library_id: UUID
    kids_mode_enabled: bool


class ListFamilyChallengesUseCase:
    """Open to any authenticated library member — the whole point is
    everyone sees and works toward the same shared goal."""

    def __init__(self, challenge_repo: FamilyChallengeRepository) -> None:
        self._challenge_repo = challenge_repo

    async def execute(self, input: ListFamilyChallengesInput) -> list[FamilyChallenge]:
        if not input.kids_mode_enabled:
            raise PermissionError("Kids mode is not enabled for this library")
        return await self._challenge_repo.list_by_library(input.library_id)


@dataclass
class DeleteFamilyChallengeInput:
    challenge_id: UUID
    library_id: UUID
    kids_mode_enabled: bool


class DeleteFamilyChallengeUseCase:
    """Parent-only (require_parent enforced at the endpoint)."""

    def __init__(self, challenge_repo: FamilyChallengeRepository) -> None:
        self._challenge_repo = challenge_repo

    async def execute(self, input: DeleteFamilyChallengeInput) -> None:
        if not input.kids_mode_enabled:
            raise PermissionError("Kids mode is not enabled for this library")
        challenge = await self._challenge_repo.find_by_id(input.challenge_id)
        if challenge is None:
            raise LookupError("Family challenge not found")
        if challenge.library_id != input.library_id:
            raise PermissionError("Family challenge does not belong to this library")
        await self._challenge_repo.delete(input.challenge_id)
        logger.info("Family challenge %s deleted from library %s", input.challenge_id, input.library_id)


@dataclass
class GetFamilyChallengeProgressInput:
    challenge_id: UUID
    library_id: UUID
    kids_mode_enabled: bool


@dataclass
class FamilyChallengeProgress:
    challenge: FamilyChallenge
    current: int


class GetFamilyChallengeProgressUseCase:
    """A single cooperative number, summed across every member of the
    library within the challenge window — deliberately never broken down
    per member (see FamilyChallenge's docstring: no leaderboard, ever)."""

    def __init__(
        self,
        challenge_repo: FamilyChallengeRepository,
        session_repo: ReadingSessionRepository,
        read_repo: BookReadRepository,
    ) -> None:
        self._challenge_repo = challenge_repo
        self._session_repo = session_repo
        self._read_repo = read_repo

    async def execute(self, input: GetFamilyChallengeProgressInput) -> FamilyChallengeProgress:
        if not input.kids_mode_enabled:
            raise PermissionError("Kids mode is not enabled for this library")
        challenge = await self._challenge_repo.find_by_id(input.challenge_id)
        if challenge is None:
            raise LookupError("Family challenge not found")
        if challenge.library_id != input.library_id:
            raise PermissionError("Family challenge does not belong to this library")

        current: int
        if challenge.metric == ChallengeMetric.BOOKS:
            reads = await self._read_repo.list_by_library(input.library_id)
            current = sum(
                1 for r in reads if challenge.starts_on <= r.read_at.date() <= challenge.ends_on
            )
        else:
            sessions = await self._session_repo.list_by_library(input.library_id)
            in_window = [s for s in sessions if challenge.starts_on <= s.session_date <= challenge.ends_on]
            if challenge.metric == ChallengeMetric.MINUTES:
                current = sum(s.minutes or 0 for s in in_window)
            else:
                current = len(in_window)

        return FamilyChallengeProgress(challenge=challenge, current=current)
