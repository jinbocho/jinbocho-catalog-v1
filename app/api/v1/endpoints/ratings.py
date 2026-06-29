from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_book_rating_repository,
    get_current_user_payload,
    get_owned_book_repository,
    require_role,
)
from app.api.v1.schemas.book_schemas import (
    BookRatingCreate,
    BookRatingResponse,
    BookRatingUpdate,
    FamilyRatingStatsResponse,
)
from app.application.use_cases import (
    CreateBookRatingInput,
    CreateBookRatingUseCase,
    DeleteBookRatingUseCase,
    GetBookRatingStatsUseCase,
    ListBookRatingsUseCase,
    ListFamilyRatingsUseCase,
    UpdateBookRatingInput,
    UpdateBookRatingUseCase,
)
from app.domain.repositories import BookRatingRepository, OwnedBookRepository
from app.infrastructure.database.session import get_db

router = APIRouter(tags=["ratings"])
family_router = APIRouter(tags=["ratings"])


@family_router.get(
    "/",
    response_model=list[BookRatingResponse],
    summary="List all family ratings",
    description="Returns every rating submitted by any member of the current family, across all books.",
)
async def list_all_family_ratings(
    payload: dict[str, Any] = Depends(get_current_user_payload),
    rating_repo: BookRatingRepository = Depends(get_book_rating_repository),
) -> list[BookRatingResponse]:
    family_id = UUID(payload["family_id"])
    ratings = await ListFamilyRatingsUseCase(rating_repo).execute(family_id)
    return [BookRatingResponse.model_validate(r) for r in ratings]


@router.get(
    "/{book_id}/ratings/stats",
    response_model=FamilyRatingStatsResponse,
    summary="Get family rating stats for a book",
    description="Returns the average rating and star distribution across all family members for the given book.",
)
async def get_rating_stats(
    book_id: UUID,
    payload: dict[str, Any] = Depends(get_current_user_payload),
    book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
    rating_repo: BookRatingRepository = Depends(get_book_rating_repository),
) -> FamilyRatingStatsResponse:
    family_id = UUID(payload["family_id"])
    stats = await GetBookRatingStatsUseCase(book_repo, rating_repo).execute(book_id, family_id)
    return FamilyRatingStatsResponse(
        owned_book_id=stats.owned_book_id,
        total=stats.total,
        average=stats.average,
        distribution=stats.distribution,
    )


@router.get(
    "/{book_id}/ratings",
    response_model=list[BookRatingResponse],
    summary="List ratings for a book",
    description="Returns all family member ratings for the given book copy.",
)
async def list_ratings(
    book_id: UUID,
    payload: dict[str, Any] = Depends(get_current_user_payload),
    book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
    rating_repo: BookRatingRepository = Depends(get_book_rating_repository),
) -> list[BookRatingResponse]:
    family_id = UUID(payload["family_id"])
    ratings = await ListBookRatingsUseCase(book_repo, rating_repo).execute(book_id, family_id)
    return [BookRatingResponse.model_validate(r) for r in ratings]


@router.post(
    "/{book_id}/ratings",
    response_model=BookRatingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Rate a book",
    description="Submit a star rating (1-5) and optional review for a book copy. One rating per member per book.",
    responses={
        409: {"description": "You have already rated this book"},
        403: {"description": "Insufficient role"},
        404: {"description": "Book not found"},
    },
)
async def create_rating(
    book_id: UUID,
    body: BookRatingCreate,
    payload: dict[str, Any] = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
    book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
    rating_repo: BookRatingRepository = Depends(get_book_rating_repository),
) -> BookRatingResponse:
    family_id = UUID(payload["family_id"])
    user_id = UUID(payload["sub"])
    rating = await CreateBookRatingUseCase(book_repo, rating_repo).execute(
        CreateBookRatingInput(
            book_id=book_id,
            family_id=family_id,
            user_id=user_id,
            rating=body.rating,
            review=body.review,
        )
    )
    await db.commit()
    return BookRatingResponse.model_validate(rating)


@router.patch(
    "/{book_id}/ratings/{rating_id}",
    response_model=BookRatingResponse,
    summary="Update your rating",
    description="Update your star rating or review. Only the author of the rating can modify it.",
    responses={
        403: {"description": "Cannot modify another user's rating or insufficient role"},
        404: {"description": "Rating or book not found"},
    },
)
async def update_rating(
    book_id: UUID,
    rating_id: UUID,
    body: BookRatingUpdate,
    payload: dict[str, Any] = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
    book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
    rating_repo: BookRatingRepository = Depends(get_book_rating_repository),
) -> BookRatingResponse:
    family_id = UUID(payload["family_id"])
    user_id = UUID(payload["sub"])
    rating = await UpdateBookRatingUseCase(book_repo, rating_repo).execute(
        UpdateBookRatingInput(
            rating_id=rating_id,
            book_id=book_id,
            family_id=family_id,
            user_id=user_id,
            rating=body.rating,
            review=body.review,
        )
    )
    await db.commit()
    return BookRatingResponse.model_validate(rating)


@router.delete(
    "/{book_id}/ratings/{rating_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete your rating",
    description="Delete your rating for this book. Only the author of the rating can delete it.",
    responses={
        403: {"description": "Cannot delete another user's rating or insufficient role"},
        404: {"description": "Rating or book not found"},
    },
)
async def delete_rating(
    book_id: UUID,
    rating_id: UUID,
    payload: dict[str, Any] = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
    book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
    rating_repo: BookRatingRepository = Depends(get_book_rating_repository),
) -> None:
    family_id = UUID(payload["family_id"])
    user_id = UUID(payload["sub"])
    await DeleteBookRatingUseCase(book_repo, rating_repo).execute(rating_id, family_id, user_id)
    await db.commit()
