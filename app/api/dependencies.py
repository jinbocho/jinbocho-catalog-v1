from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domain.repositories import (
    BibliographicRecordRepository,
    BookHistoryRepository,
    BookLoanRepository,
    BookReadRepository,
    BookcaseRepository,
    IsbnLookupCacheRepository,
    OwnedBookRepository,
    RemovedMemberRepository,
    RoomRepository,
    SectionRepository,
    ShelfRepository,
)
from app.infrastructure.database.session import get_db
from app.infrastructure.repositories import (
    SQLAlchemyBibliographicRecordRepository,
    SQLAlchemyBookHistoryRepository,
    SQLAlchemyBookLoanRepository,
    SQLAlchemyBookReadRepository,
    SQLAlchemyBookcaseRepository,
    SQLAlchemyIsbnLookupCacheRepository,
    SQLAlchemyOwnedBookRepository,
    SQLAlchemyRemovedMemberRepository,
    SQLAlchemyRoomRepository,
    SQLAlchemySectionRepository,
    SQLAlchemyShelfRepository,
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
        )

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
    return request.app.state.http_client


def require_role(*roles: str):
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
