import logging
import re
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import BibliographicRecord, MysteryPick, MysteryPickStatus
from app.domain.repositories import BibliographicRecordRepository, MysteryPickRepository, OwnedBookRepository

logger = logging.getLogger(__name__)

_HINT_MAX_LENGTH = 220


def _mask_hint(record: BibliographicRecord) -> str:
    """Reuses the incipit feature's text but strips any direct giveaway —
    the title and author, wherever they appear — and trims it to a teaser
    length. Falls back to a genre-only hint when there's no incipit yet."""
    if not record.incipit:
        genre = record.genre or "great"
        return f"A {genre} book is waiting for you on the shelf. Can you guess which one?"

    masked = record.incipit
    for giveaway in (record.title, record.main_author):
        if giveaway:
            masked = re.sub(re.escape(giveaway), "...", masked, flags=re.IGNORECASE)

    if len(masked) > _HINT_MAX_LENGTH:
        masked = masked[:_HINT_MAX_LENGTH].rsplit(" ", 1)[0] + "..."
    return masked


@dataclass
class CreateMysteryPickInput:
    library_id: UUID
    owned_book_id: UUID
    child_user_id: UUID
    created_by: UUID
    kids_mode_enabled: bool


class CreateMysteryPickUseCase:
    """Parent-only (require_parent enforced at the endpoint)."""

    def __init__(
        self,
        book_repo: OwnedBookRepository,
        record_repo: BibliographicRecordRepository,
        pick_repo: MysteryPickRepository,
    ) -> None:
        self._book_repo = book_repo
        self._record_repo = record_repo
        self._pick_repo = pick_repo

    async def execute(self, input: CreateMysteryPickInput) -> MysteryPick:
        if not input.kids_mode_enabled:
            raise PermissionError("Kids mode is not enabled for this library")
        book = await self._book_repo.find_by_id(input.owned_book_id)
        if not book:
            raise LookupError("Book not found")
        if book.library_id != input.library_id:
            raise PermissionError("Book does not belong to this library")
        record = await self._record_repo.find_by_id(book.bibliographic_record_id)
        if not record:
            raise LookupError("BibliographicRecord not found")

        pick = MysteryPick(
            library_id=input.library_id,
            owned_book_id=input.owned_book_id,
            child_user_id=input.child_user_id,
            hint_text=_mask_hint(record),
            status=MysteryPickStatus.PROPOSED,
            created_by=input.created_by,
        )
        saved = await self._pick_repo.add(pick)
        logger.info(
            "Mystery pick %s proposed for child %s in library %s", saved.id, input.child_user_id, input.library_id
        )
        return saved


@dataclass
class AcceptMysteryPickInput:
    pick_id: UUID
    library_id: UUID
    requester_user_id: UUID
    kids_mode_enabled: bool


class AcceptMysteryPickUseCase:
    """Only the target child can accept — accepting is also the reveal
    moment (see MysteryPickStatus.ACCEPTED)."""

    def __init__(self, pick_repo: MysteryPickRepository) -> None:
        self._pick_repo = pick_repo

    async def execute(self, input: AcceptMysteryPickInput) -> MysteryPick:
        if not input.kids_mode_enabled:
            raise PermissionError("Kids mode is not enabled for this library")
        pick = await self._pick_repo.find_by_id(input.pick_id)
        if pick is None:
            raise LookupError("Mystery pick not found")
        if pick.library_id != input.library_id:
            raise PermissionError("Mystery pick does not belong to this library")
        if pick.child_user_id != input.requester_user_id:
            raise PermissionError("Only the child this pick was proposed to can accept it")

        pick.status = MysteryPickStatus.ACCEPTED
        saved = await self._pick_repo.save(pick)
        logger.info("Mystery pick %s accepted by %s", saved.id, input.requester_user_id)
        return saved


@dataclass
class ListMysteryPicksInput:
    child_user_id: UUID
    library_id: UUID
    requester_user_id: UUID
    requester_role: str
    kids_mode_enabled: bool


class ListMysteryPicksUseCase:
    """A child sees only their own picks; a parent (admin/editor) can view
    any child's, same self-or-parent pattern as reading sessions/journal."""

    def __init__(self, pick_repo: MysteryPickRepository) -> None:
        self._pick_repo = pick_repo

    async def execute(self, input: ListMysteryPicksInput) -> list[MysteryPick]:
        if not input.kids_mode_enabled:
            raise PermissionError("Kids mode is not enabled for this library")
        is_self = input.child_user_id == input.requester_user_id
        is_parent = input.requester_role in ("admin", "editor")
        if not is_self and not is_parent:
            raise PermissionError("Cannot view another child's mystery picks")
        return await self._pick_repo.list_by_child(input.child_user_id, input.library_id)
