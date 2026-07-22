from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases import FuzzyDedupConfig
from app.config import settings
from app.domain.repositories import (
    BibliographicRecordRepository,
    BookAbandonmentRepository,
    BookcaseRepository,
    BookClubCycleRepository,
    BookClubMeetingRepository,
    BookClubParticipantRepository,
    BookClubPostRepository,
    BookClubProposalRepository,
    BookClubQuestionSetRepository,
    BookClubVoteRepository,
    BookHistoryRepository,
    BookLoanRepository,
    BookRatingRepository,
    BookReadRepository,
    BookSearchProvider,
    DiscussionQuestionGenerator,
    DiscussionQuestionSetRepository,
    DuplicateJudge,
    FamilyChallengeRepository,
    IsbnLookupCacheRepository,
    IsbnMetadataFetcher,
    JournalEntryRepository,
    MysteryPickRepository,
    OwnedBookRepository,
    QuizAttemptRepository,
    QuizGenerator,
    QuizQuestionRepository,
    ReadingPathRepository,
    ReadingSessionRepository,
    RemovedMemberRepository,
    RoomRepository,
    SectionRepository,
    ShelfRepository,
    ShelfSpineReader,
    WishlistRepository,
)
from app.infrastructure.database.session import get_db
from app.infrastructure.external import (
    AiDiscussionClient,
    AiIncipitClient,
    AiQuizClient,
    AiServiceConfig,
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
    SQLAlchemyBookAbandonmentRepository,
    SQLAlchemyBookcaseRepository,
    SQLAlchemyBookClubCycleRepository,
    SQLAlchemyBookClubMeetingRepository,
    SQLAlchemyBookClubParticipantRepository,
    SQLAlchemyBookClubPostRepository,
    SQLAlchemyBookClubProposalRepository,
    SQLAlchemyBookClubQuestionSetRepository,
    SQLAlchemyBookClubVoteRepository,
    SQLAlchemyBookHistoryRepository,
    SQLAlchemyBookLoanRepository,
    SQLAlchemyBookRatingRepository,
    SQLAlchemyBookReadRepository,
    SQLAlchemyDiscussionQuestionSetRepository,
    SQLAlchemyFamilyChallengeRepository,
    SQLAlchemyIsbnLookupCacheRepository,
    SQLAlchemyJournalEntryRepository,
    SQLAlchemyMysteryPickRepository,
    SQLAlchemyOwnedBookRepository,
    SQLAlchemyQuizAttemptRepository,
    SQLAlchemyQuizQuestionRepository,
    SQLAlchemyReadingPathRepository,
    SQLAlchemyReadingSessionRepository,
    SQLAlchemyRemovedMemberRepository,
    SQLAlchemyRoomRepository,
    SQLAlchemySectionRepository,
    SQLAlchemyShelfRepository,
    SQLAlchemyWishlistRepository,
)

# auto_error=False: fastapi>=0.116/starlette>=1.0 changed HTTPBearer's own
# missing-credentials response from 403 to 401 — the app's established
# contract, relied on by the FE's 401-triggers-refresh logic, is 403 for "no
# credentials at all" vs 401 for "credentials present but invalid/expired".
# Handling it explicitly here keeps that contract stable regardless of what
# the library defaults to.
security = HTTPBearer(auto_error=False)


async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "sub", "library_id", "aud", "iss"]},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    library_id_str = payload.get("library_id")
    sub = payload.get("sub")
    if not library_id_str or not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required claims",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client  # type: ignore[no-any-return]


def get_ai_service_config() -> AiServiceConfig:
    return AiServiceConfig(
        enabled=settings.ai_module_enabled,
        url=settings.ai_service_url,
        internal_token=settings.ai_internal_service_token,
    )


def get_duplicate_judge(
    http_client: httpx.AsyncClient = Depends(get_http_client),
    config: AiServiceConfig = Depends(get_ai_service_config),
) -> DuplicateJudge:
    return HttpDuplicateJudge(http_client, config)


def get_quiz_generator(
    http_client: httpx.AsyncClient = Depends(get_http_client),
    config: AiServiceConfig = Depends(get_ai_service_config),
) -> QuizGenerator:
    return AiQuizClient(http_client, config)


def get_discussion_generator(
    http_client: httpx.AsyncClient = Depends(get_http_client),
    config: AiServiceConfig = Depends(get_ai_service_config),
) -> DiscussionQuestionGenerator:
    return AiDiscussionClient(http_client, config)


async def get_discussion_question_set_repository(
    db: AsyncSession = Depends(get_db),
) -> DiscussionQuestionSetRepository:
    return SQLAlchemyDiscussionQuestionSetRepository(db)


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
            open_library_covers_url=settings.open_library_covers_url,
            cover_size=settings.open_library_cover_size,
        ),
    )


def get_book_search_provider(http_client: httpx.AsyncClient = Depends(get_http_client)) -> BookSearchProvider:
    return HttpBookSearchProvider(
        http_client,
        BookSearchConfig(
            google_books_url=settings.google_books_url,
            google_books_api_key=settings.google_books_api_key,
            open_library_url=settings.open_library_url,
            open_library_covers_url=settings.open_library_covers_url,
            cover_size=settings.open_library_cover_size,
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


# Kids-mode role gates (own copy — auth-service's require_child/require_parent
# are a separate process/DB, not importable here). "child" never appears in
# any other require_role(...) allowlist in this service, so every existing
# catalog endpoint already default-denies a child token.
require_child = require_role("child")
require_parent = require_role("admin", "editor")
# Quiz generation is the one kids-mode action either side can trigger: a
# child self-serves it, a parent may prefer to prepare/review it before
# handing the book over. Scoring/logging stay strictly require_child — those
# are personal actions, not delegable.
require_child_or_parent = require_role("child", "admin", "editor")


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


async def get_reading_session_repository(db: AsyncSession = Depends(get_db)) -> ReadingSessionRepository:
    return SQLAlchemyReadingSessionRepository(db)


async def get_journal_entry_repository(db: AsyncSession = Depends(get_db)) -> JournalEntryRepository:
    return SQLAlchemyJournalEntryRepository(db)


async def get_reading_path_repository(db: AsyncSession = Depends(get_db)) -> ReadingPathRepository:
    return SQLAlchemyReadingPathRepository(db)


async def get_mystery_pick_repository(db: AsyncSession = Depends(get_db)) -> MysteryPickRepository:
    return SQLAlchemyMysteryPickRepository(db)


async def get_family_challenge_repository(db: AsyncSession = Depends(get_db)) -> FamilyChallengeRepository:
    return SQLAlchemyFamilyChallengeRepository(db)


async def get_quiz_question_repository(db: AsyncSession = Depends(get_db)) -> QuizQuestionRepository:
    return SQLAlchemyQuizQuestionRepository(db)


async def get_quiz_attempt_repository(db: AsyncSession = Depends(get_db)) -> QuizAttemptRepository:
    return SQLAlchemyQuizAttemptRepository(db)


async def get_isbn_lookup_cache_repository(
    db: AsyncSession = Depends(get_db),
) -> IsbnLookupCacheRepository:
    return SQLAlchemyIsbnLookupCacheRepository(db)


async def get_removed_member_repository(db: AsyncSession = Depends(get_db)) -> RemovedMemberRepository:
    return SQLAlchemyRemovedMemberRepository(db)


async def get_book_read_repository(db: AsyncSession = Depends(get_db)) -> BookReadRepository:
    return SQLAlchemyBookReadRepository(db)


async def get_book_abandonment_repository(db: AsyncSession = Depends(get_db)) -> BookAbandonmentRepository:
    return SQLAlchemyBookAbandonmentRepository(db)


async def get_book_loan_repository(db: AsyncSession = Depends(get_db)) -> BookLoanRepository:
    return SQLAlchemyBookLoanRepository(db)


async def get_wishlist_repository(db: AsyncSession = Depends(get_db)) -> WishlistRepository:
    return SQLAlchemyWishlistRepository(db)


async def get_book_rating_repository(db: AsyncSession = Depends(get_db)) -> BookRatingRepository:
    return SQLAlchemyBookRatingRepository(db)


async def get_book_club_cycle_repository(
    db: AsyncSession = Depends(get_db),
) -> BookClubCycleRepository:
    return SQLAlchemyBookClubCycleRepository(db)


async def get_book_club_post_repository(
    db: AsyncSession = Depends(get_db),
) -> BookClubPostRepository:
    return SQLAlchemyBookClubPostRepository(db)


async def get_book_club_proposal_repository(
    db: AsyncSession = Depends(get_db),
) -> BookClubProposalRepository:
    return SQLAlchemyBookClubProposalRepository(db)


async def get_book_club_vote_repository(
    db: AsyncSession = Depends(get_db),
) -> BookClubVoteRepository:
    return SQLAlchemyBookClubVoteRepository(db)


async def get_book_club_participant_repository(
    db: AsyncSession = Depends(get_db),
) -> BookClubParticipantRepository:
    return SQLAlchemyBookClubParticipantRepository(db)


async def get_book_club_meeting_repository(
    db: AsyncSession = Depends(get_db),
) -> BookClubMeetingRepository:
    return SQLAlchemyBookClubMeetingRepository(db)


async def get_book_club_question_set_repository(
    db: AsyncSession = Depends(get_db),
) -> BookClubQuestionSetRepository:
    return SQLAlchemyBookClubQuestionSetRepository(db)
