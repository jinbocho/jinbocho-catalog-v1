from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
	get_current_user_payload,
	get_http_client,
	get_isbn_lookup_cache_repository,
	get_isbn_lookup_config,
	require_role,
)
from app.api.v1.schemas.ingestion_schemas import BookSearchResponse, BulkLookupRequest, IsbnLookupResponse
from app.application.use_cases import BulkLookupIsbnUseCase, LookupIsbnUseCase, SearchBooksUseCase
from app.application.use_cases.ingestion.lookup_isbn import IsbnLookupConfig
from app.domain.repositories import IsbnLookupCacheRepository
from app.infrastructure.database.session import get_db
from app.limiter import limiter

router = APIRouter(tags=["ingestion"])


@router.get("/isbn/{isbn}", response_model=IsbnLookupResponse, summary="Lookup ISBN metadata")
@limiter.limit("30/minute")
async def lookup_isbn(
	isbn: str,
	request: Request,
	payload: dict[str, Any] = Depends(get_current_user_payload),
	db: AsyncSession = Depends(get_db),
	cache_repo: IsbnLookupCacheRepository = Depends(get_isbn_lookup_cache_repository),
	http_client: httpx.AsyncClient = Depends(get_http_client),
	config: IsbnLookupConfig = Depends(get_isbn_lookup_config),
) -> IsbnLookupResponse:
	result = await LookupIsbnUseCase(cache_repo, http_client, config).execute(isbn)
	await db.commit()
	return IsbnLookupResponse(source=result.source, metadata=result.metadata, cached=result.cached)


@router.get("/search", response_model=BookSearchResponse, summary="Search books online by title/author")
@limiter.limit("30/minute")
async def search_books(
	request: Request,
	title: str | None = Query(default=None, min_length=1, max_length=200),
	author: str | None = Query(default=None, min_length=1, max_length=200),
	payload: dict[str, Any] = Depends(get_current_user_payload),
	http_client: httpx.AsyncClient = Depends(get_http_client),
) -> BookSearchResponse:
	if not title and not author:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide at least a title or an author")
	results = await SearchBooksUseCase(http_client).execute(title, author)
	return BookSearchResponse(results=results)


@router.post("/bulk-lookup", summary="Bulk ISBN lookup", response_model=None)
@limiter.limit("5/minute")
async def bulk_lookup(
	body: BulkLookupRequest,
	request: Request,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	cache_repo: IsbnLookupCacheRepository = Depends(get_isbn_lookup_cache_repository),
	http_client: httpx.AsyncClient = Depends(get_http_client),
	config: IsbnLookupConfig = Depends(get_isbn_lookup_config),
) -> dict[str, Any]:
	results = await BulkLookupIsbnUseCase(cache_repo, http_client, config).execute(body.isbns)
	await db.commit()
	return {"results": results}
