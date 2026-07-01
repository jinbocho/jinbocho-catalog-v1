from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.catalog.add_book import FuzzyDedupConfig
from app.config import settings
from app.domain.repositories import (
    BibliographicRecordRepository,
    BookRatingRepository,
    BookSearchProvider,
    BookcaseRepository,
    BookHistoryRepository,
    BookLoanRepository,
    BookReadRepository,
    DuplicateJudge,
    IsbnLookupCacheRepository,
    IsbnMetadataFetcher,
    OwnedBookRepository,
    RemovedMemberRepository,
    RoomRepository,
    SectionRepository,
    ShelfRepository,
    ShelfSpineReader,
    WishlistRepository,
)
from app.infrastructure.database.session import get_db
from app.infrastructure.external import (
    AiIncipitClient,
    AiShelfScanClient,
    AiTagsClient,
    BookSearchConfig,
    HttpBookSearchProvider,
    HttpDuplicateJudge,
    HttpIsbnMetadataFetcher,
    IsbnLookupConfig,
    OpenLibraryDescriptionFetcher,
)
from app.infrastructure.repositories import (
    SQLAlchemyBibliographicRecordRepository,
    SQLAlchemyBookcaseRepository,
    SQLAlchemyBookHistoryRepository,
    SQLAlchemyBookLoanRepository,
    SQLAlchemyBookRatingRepository,
    SQLAlchemyBookReadRepository,
    SQLAlchemyIsbnLookupCacheRepository,
    SQLAlchemyOwnedBookRepository,
    SQLAlchemyRemovedMemberRepository,
    SQLAlchemyRoomRepository,
    SQLAlchemySectionRepository,
    SQLAlchemyShelfRepository,
    SQLAlchemyWishlistRepository,
)

security = HTTPBearer()


async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "sub", "family_id", "aud", "iss"]},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    family_id_str = payload.get("family_id")
    sub = payload.get("sub")
    if not family_id_str or not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required claims",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client  # type: ignore[no-any-return]


def get_duplicate_judge(http_client: httpx.AsyncClient = Depends(get_http_client)) -> DuplicateJudge:
    return HttpDuplicateJudge(http_client)


def get_ai_incipit_client(http_client: httpx.AsyncClient = Depends(get_http_client)) -> AiIncipitClient:
    return AiIncipitClient(http_client, settings.ai_service_url)


def get_editorial_description_provider(
    http_client: httpx.AsyncClient = Depends(get_http_client),
) -> OpenLibraryDescriptionFetcher:
    return OpenLibraryDescriptionFetcher(http_client, settings.open_library_url)


def get_tag_suggester(http_client: httpx.AsyncClient = Depends(get_http_client)) -> AiTagsClient:
    return AiTagsClient(http_client, settings.ai_service_url)


def get_shelf_spine_reader(http_client: httpx.AsyncClient = Depends(get_http_client)) -> ShelfSpineReader:
    return AiShelfScanClient(http_client, settings.ai_service_url)


def get_isbn_metadata_fetcher(http_client: httpx.AsyncClient = Depends(get_http_client)) -> IsbnMetadataFetcher:
    return HttpIsbnMetadataFetcher(
        http_client,
        IsbnLookupConfig(
            google_books_url=settings.google_books_url,
            google_books_api_key=settings.google_books_api_key,
            open_library_url=settings.open_library_url,
        ),
    )


def get_book_search_provider(http_client: httpx.AsyncClient = Depends(get_http_client)) -> BookSearchProvider:
    return HttpBookSearchProvider(
        http_client,
        BookSearchConfig(
            google_books_url=settings.google_books_url,
            google_books_api_key=settings.google_books_api_key,
            open_library_url=settings.open_library_url,
        ),
    )


def get_fuzzy_dedup_config() -> FuzzyDedupConfig:
    return FuzzyDedupConfig(
        high_threshold=settings.fuzzy_dedup_high_threshold,
        low_threshold=settings.fuzzy_dedup_low_threshold,
    )


def require_role(*roles: str) -> Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]:
    async def dependency(payload: dict[str, Any] = Depends(get_current_user_payload)) -> dict[str, Any]:
        if payload.get("role") not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return payload

    return dependency


async def get_room_repository(db: AsyncSession = Depends(get_db)) -> RoomRepository:
    return SQLAlchemyRoomRepository(db)


async def get_bookcase_repository(db: AsyncSession = Depends(get_db)) -> BookcaseRepository:
    return SQLAlchemyBookcaseRepository(db)


async def get_section_repository(db: AsyncSession = Depends(get_db)) -> SectionRepository:
    return SQLAlchemySectionRepository(db)


async def get_shelf_repository(db: AsyncSession = Depends(get_db)) -> ShelfRepository:
    return SQLAlchemyShelfRepository(db)


async def get_bibliographic_record_repository(
    db: AsyncSession = Depends(get_db),
) -> BibliographicRecordRepository:
    return SQLAlchemyBibliographicRecordRepository(db)


async def get_owned_book_repository(db: AsyncSession = Depends(get_db)) -> OwnedBookRepository:
    return SQLAlchemyOwnedBookRepository(db)


async def get_book_history_repository(db: AsyncSession = Depends(get_db)) -> BookHistoryRepository:
    return SQLAlchemyBookHistoryRepository(db)


async def get_isbn_lookup_cache_repository(
    db: AsyncSession = Depends(get_db),
) -> IsbnLookupCacheRepository:
    return SQLAlchemyIsbnLookupCacheRepository(db)


async def get_removed_member_repository(db: AsyncSession = Depends(get_db)) -> RemovedMemberRepository:
    return SQLAlchemyRemovedMemberRepository(db)


async def get_book_read_repository(db: AsyncSession = Depends(get_db)) -> BookReadRepository:
    return SQLAlchemyBookReadRepository(db)


async def get_book_loan_repository(db: AsyncSession = Depends(get_db)) -> BookLoanRepository:
    return SQLAlchemyBookLoanRepository(db)


async def get_wishlist_repository(db: AsyncSession = Depends(get_db)) -> WishlistRepository:
    return SQLAlchemyWishlistRepository(db)


async def get_book_rating_repository(db: AsyncSession = Depends(get_db)) -> BookRatingRepository:
    return SQLAlchemyBookRatingRepository(db)
