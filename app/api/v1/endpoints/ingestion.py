import asyncio
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_payload, get_http_client, get_isbn_lookup_cache_repository, require_role
from app.application.use_cases import LookupIsbnUseCase
from app.domain.repositories import IsbnLookupCacheRepository
from app.infrastructure.database.session import AsyncSessionLocal, get_db
from app.infrastructure.repositories import SQLAlchemyIsbnLookupCacheRepository
from app.limiter import limiter

router = APIRouter()


class IngestionMetadataResponse(BaseModel):
    source: str
    metadata: dict
    cached: bool = False


class BulkLookupRequest(BaseModel):
    isbns: list[str] = Field(min_length=1, max_length=20)


class BulkLookupItem(BaseModel):
    isbn: str
    ok: bool
    data: dict | None = None
    error: str | None = None


class BulkLookupResponse(BaseModel):
    results: list[BulkLookupItem]


@router.get("/isbn/{isbn}", response_model=IngestionMetadataResponse)
@limiter.limit("30/minute")
async def lookup_isbn(
    request: Request,
    isbn: str,
    payload: dict = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db),
    cache_repo: IsbnLookupCacheRepository = Depends(get_isbn_lookup_cache_repository),
    http_client: httpx.AsyncClient = Depends(get_http_client),
):
    _ = payload
    use_case = LookupIsbnUseCase(cache_repo=cache_repo, http_client=http_client)
    try:
        result = await use_case.execute(isbn.replace("-", "").strip())
        await db.commit()
        return IngestionMetadataResponse(source=result.source, metadata=result.metadata, cached=result.cached)
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/bulk", response_model=BulkLookupResponse, status_code=status.HTTP_200_OK)
@router.post("/isbn/bulk", response_model=BulkLookupResponse, include_in_schema=False, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def bulk_lookup(
    request: Request,
    body: BulkLookupRequest,
    payload: dict = Depends(require_role("admin", "editor")),
    http_client: httpx.AsyncClient = Depends(get_http_client),
):
    _ = (request, payload)

    async def process_isbn(raw_isbn: str) -> BulkLookupItem:
        isbn = raw_isbn.replace("-", "").strip()
        async with AsyncSessionLocal() as session:
            repo = SQLAlchemyIsbnLookupCacheRepository(session)
            use_case = LookupIsbnUseCase(cache_repo=repo, http_client=http_client)
            try:
                result = await use_case.execute(isbn)
                await session.commit()
                return BulkLookupItem(isbn=isbn, ok=True, data={"source": result.source, "metadata": result.metadata, "cached": result.cached})
            except (LookupError, httpx.HTTPError, asyncio.TimeoutError) as exc:
                await session.rollback()
                return BulkLookupItem(isbn=isbn, ok=False, error=str(exc))

    results = await asyncio.gather(*[process_isbn(raw_isbn) for raw_isbn in body.isbns], return_exceptions=True)
    normalized: list[BulkLookupItem] = []
    for raw_isbn, result in zip(body.isbns, results):
        if isinstance(result, Exception):
            normalized.append(BulkLookupItem(isbn=raw_isbn.replace("-", "").strip(), ok=False, error=str(result)))
        else:
            normalized.append(result)
    return BulkLookupResponse(results=normalized)
