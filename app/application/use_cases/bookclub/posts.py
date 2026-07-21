import logging
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import BookClubPost
from app.domain.entities.book_club_cycle import BookClubCycleStatus
from app.domain.repositories import BookClubCycleRepository, BookClubPostRepository

logger = logging.getLogger(__name__)


@dataclass
class AddPostInput:
    cycle_id: UUID
    library_id: UUID
    user_id: UUID
    body: str
    parent_post_id: UUID | None = None
    is_spoiler: bool = False


class AddPostUseCase:
    def __init__(
        self, cycle_repo: BookClubCycleRepository, post_repo: BookClubPostRepository
    ) -> None:
        self._cycle_repo = cycle_repo
        self._post_repo = post_repo

    async def execute(self, inp: AddPostInput) -> BookClubPost:
        cycle = await self._cycle_repo.find_by_id(inp.cycle_id)
        if cycle is None:
            raise LookupError("Cycle not found")
        if cycle.library_id != inp.library_id:
            raise PermissionError("Cycle does not belong to this library")
        # Discussion is a distinct phase: only opens once the manager advances
        # the cycle past reading, via AdvanceCycleStatusUseCase.
        if cycle.status is not BookClubCycleStatus.DISCUSSING:
            raise PermissionError("Discussion is not open for this cycle yet")
        if inp.parent_post_id is not None:
            parent = await self._post_repo.find_by_id(inp.parent_post_id)
            if parent is None:
                raise LookupError("Parent post not found")
            if parent.cycle_id != inp.cycle_id:
                raise ValueError("Parent post belongs to a different cycle")
        saved = await self._post_repo.add(
            BookClubPost(
                cycle_id=inp.cycle_id,
                user_id=inp.user_id,
                body=inp.body,
                parent_post_id=inp.parent_post_id,
                is_spoiler=inp.is_spoiler,
            )
        )
        logger.info("Post %s added to cycle %s", saved.id, inp.cycle_id)
        return saved


class ListPostsUseCase:
    def __init__(
        self, cycle_repo: BookClubCycleRepository, post_repo: BookClubPostRepository
    ) -> None:
        self._cycle_repo = cycle_repo
        self._post_repo = post_repo

    async def execute(self, cycle_id: UUID, library_id: UUID) -> list[BookClubPost]:
        cycle = await self._cycle_repo.find_by_id(cycle_id)
        if cycle is None:
            raise LookupError("Cycle not found")
        if cycle.library_id != library_id:
            raise PermissionError("Cycle does not belong to this library")
        return await self._post_repo.list_by_cycle(cycle_id)


class DeletePostUseCase:
    def __init__(
        self, cycle_repo: BookClubCycleRepository, post_repo: BookClubPostRepository
    ) -> None:
        self._cycle_repo = cycle_repo
        self._post_repo = post_repo

    async def execute(
        self, post_id: UUID, library_id: UUID, user_id: UUID, is_admin: bool
    ) -> None:
        post = await self._post_repo.find_by_id(post_id)
        if post is None:
            raise LookupError("Post not found")
        cycle = await self._cycle_repo.find_by_id(post.cycle_id)
        if cycle is None or cycle.library_id != library_id:
            raise PermissionError("Post does not belong to this library")
        if post.user_id != user_id and not is_admin:
            raise PermissionError("Cannot delete another user's post")
        await self._post_repo.delete(post)
        logger.info("Post %s deleted from cycle %s", post_id, post.cycle_id)
