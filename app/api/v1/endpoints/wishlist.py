from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_bibliographic_record_repository,
    get_current_user_payload,
    get_wishlist_repository,
    require_role,
)
from app.api.v1.schemas.record_schemas import BibliographicRecordResponse
from app.api.v1.schemas.wishlist_schemas import WishlistItemCreate, WishlistItemResponse
from app.application.use_cases import (
    AddToWishlistUseCase,
    ListFamilyWishlistUseCase,
    RemoveFromWishlistUseCase,
)
from app.application.use_cases.catalog.wishlist import AddToWishlistInput
from app.domain.entities import BibliographicRecord, WishlistItem
from app.domain.repositories import BibliographicRecordRepository, WishlistRepository
from app.infrastructure.database.session import get_db

router = APIRouter()


def _build_response(item: WishlistItem, record: BibliographicRecord) -> WishlistItemResponse:
    return WishlistItemResponse(
        id=item.id,
        family_id=item.family_id,
        user_id=item.user_id,
        bibliographic_record_id=item.bibliographic_record_id,
        added_at=item.added_at,
        notes=item.notes,
        priority=item.priority,
        record=BibliographicRecordResponse.model_validate(record),
    )


@router.get("/", response_model=list[WishlistItemResponse], summary="List family wishlist")
async def list_wishlist(
    payload: dict[str, Any] = Depends(get_current_user_payload),
    wishlist_repo: WishlistRepository = Depends(get_wishlist_repository),
    record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
) -> list[WishlistItemResponse]:
    family_id = UUID(payload["family_id"])
    items = await ListFamilyWishlistUseCase(wishlist_repo).execute(family_id)
    if not items:
        return []
    record_ids = [item.bibliographic_record_id for item in items]
    records = await record_repo.find_all_by_ids(record_ids)
    record_map = {r.id: r for r in records}
    return [
        _build_response(item, record)
        for item in items
        if (record := record_map.get(item.bibliographic_record_id)) is not None
    ]


@router.post(
    "/",
    response_model=WishlistItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a book to the family wishlist",
)
async def add_to_wishlist(
    body: WishlistItemCreate,
    payload: dict[str, Any] = Depends(require_role("admin", "editor", "viewer")),
    db: AsyncSession = Depends(get_db),
    wishlist_repo: WishlistRepository = Depends(get_wishlist_repository),
    record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
) -> WishlistItemResponse:
    family_id = UUID(payload["family_id"])
    user_id = UUID(payload["sub"])
    item = await AddToWishlistUseCase(wishlist_repo, record_repo).execute(
        AddToWishlistInput(
            family_id=family_id,
            user_id=user_id,
            bibliographic_record_id=body.bibliographic_record_id,
            title=body.title,
            isbn=body.isbn,
            main_author=body.main_author,
            other_authors=body.other_authors,
            publisher=body.publisher,
            publication_year=body.publication_year,
            language=body.language,
            genre=body.genre,
            cover_url=body.cover_url,
            notes=body.notes,
            priority=body.priority,
        )
    )
    await db.commit()
    record = await record_repo.find_by_id(item.bibliographic_record_id)
    if record is None:
        raise LookupError(f"Bibliographic record {item.bibliographic_record_id} not found after save")
    return _build_response(item, record)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a book from the wishlist",
)
async def remove_from_wishlist(
    item_id: UUID,
    payload: dict[str, Any] = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db),
    wishlist_repo: WishlistRepository = Depends(get_wishlist_repository),
) -> None:
    family_id = UUID(payload["family_id"])
    user_id = UUID(payload["sub"])
    role: str = payload.get("role", "viewer")
    await RemoveFromWishlistUseCase(wishlist_repo).execute(item_id, family_id, user_id, role)
    await db.commit()
