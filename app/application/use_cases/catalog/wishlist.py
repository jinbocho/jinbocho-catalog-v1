import logging
from dataclasses import dataclass, field
from uuid import UUID

from app.domain.entities import BibliographicRecord, WishlistItem
from app.domain.repositories import BibliographicRecordRepository, WishlistRepository

logger = logging.getLogger(__name__)


@dataclass
class AddToWishlistInput:
    family_id: UUID
    user_id: UUID
    bibliographic_record_id: UUID | None = None
    title: str | None = None
    isbn: str | None = None
    main_author: str | None = None
    other_authors: list[str] = field(default_factory=list)
    publisher: str | None = None
    publication_year: int | None = None
    language: str | None = None
    genre: str | None = None
    cover_url: str | None = None
    notes: str | None = None
    priority: int | None = None


class AddToWishlistUseCase:
    def __init__(
        self,
        wishlist_repo: WishlistRepository,
        record_repo: BibliographicRecordRepository,
    ) -> None:
        self._wishlist_repo = wishlist_repo
        self._record_repo = record_repo

    async def execute(self, inp: AddToWishlistInput) -> WishlistItem:
        if inp.bibliographic_record_id is None:
            if not inp.title:
                raise ValueError("Either bibliographic_record_id or title must be provided")
            record = BibliographicRecord(
                family_id=inp.family_id,
                title=inp.title,
                isbn=inp.isbn,
                main_author=inp.main_author,
                other_authors=inp.other_authors,
                publisher=inp.publisher,
                publication_year=inp.publication_year,
                language=inp.language,
                genre=inp.genre,
                cover_url=inp.cover_url,
            )
            record = await self._record_repo.save(record)
            bibliographic_record_id = record.id
        else:
            fetched = await self._record_repo.find_by_id(inp.bibliographic_record_id)
            if not fetched:
                raise LookupError("Bibliographic record not found")
            if fetched.family_id != inp.family_id:
                raise PermissionError("Bibliographic record does not belong to this family")
            bibliographic_record_id = inp.bibliographic_record_id

        if await self._wishlist_repo.exists_for_user_and_record(inp.user_id, bibliographic_record_id):
            raise ValueError("This book is already in your wishlist")

        saved = await self._wishlist_repo.add(
            WishlistItem(
                family_id=inp.family_id,
                user_id=inp.user_id,
                bibliographic_record_id=bibliographic_record_id,
                notes=inp.notes,
                priority=inp.priority,
            )
        )
        logger.info("Wishlist item %s added by user %s in family %s", saved.id, inp.user_id, inp.family_id)
        return saved


class RemoveFromWishlistUseCase:
    def __init__(self, wishlist_repo: WishlistRepository) -> None:
        self._wishlist_repo = wishlist_repo

    async def execute(self, item_id: UUID, family_id: UUID, user_id: UUID, role: str) -> None:
        item = await self._wishlist_repo.get(item_id, family_id)
        if not item:
            raise LookupError("Wishlist item not found")
        if item.user_id != user_id and role != "admin":
            raise PermissionError("Cannot remove another user's wishlist item")
        await self._wishlist_repo.delete(item_id, family_id)
        logger.info("Wishlist item %s removed by user %s in family %s", item_id, user_id, family_id)


class ListFamilyWishlistUseCase:
    def __init__(self, wishlist_repo: WishlistRepository) -> None:
        self._wishlist_repo = wishlist_repo

    async def execute(self, family_id: UUID) -> list[WishlistItem]:
        return await self._wishlist_repo.list_by_family(family_id)
