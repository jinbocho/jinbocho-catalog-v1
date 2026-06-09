from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_payload, get_http_client, get_isbn_lookup_cache_repository, require_role
from app.api.v1.schemas.ingestion_schemas import BulkLookupRequest, IsbnLookupResponse
from app.application.use_cases import LookupIsbnUseCase
from app.infrastructure.database.session import get_db

router = APIRouter(tags=["ingestion"])


@router.get("/isbn/{isbn}", response_model=IsbnLookupResponse, summary="Lookup ISBN metadata")
async def lookup_isbn(
	isbn: str,
	payload: dict = Depends(get_current_user_payload),
	cache_repo = Depends(get_isbn_lookup_cache_repository),
	http_client: httpx.AsyncClient = Depends(get_http_client),
):
	result = await LookupIsbnUseCase(cache_repo, http_client).execute(isbn)
	return IsbnLookupResponse(source=result.source, metadata=result.metadata, cached=result.cached)


@router.post("/bulk-lookup", summary="Bulk ISBN lookup")
async def bulk_lookup(
	request: BulkLookupRequest,
	payload: dict = Depends(require_role("admin", "editor")),
	cache_repo = Depends(get_isbn_lookup_cache_repository),
	http_client: httpx.AsyncClient = Depends(get_http_client),
):
	results = []
	for isbn in request.isbns:
		try:
			result = await LookupIsbnUseCase(cache_repo, http_client).execute(isbn)
			results.append({
				"isbn": isbn,
				"ok": True,
				"data": result.metadata,
				"error": None
			})
		except LookupError:
			results.append({
				"isbn": isbn,
				"ok": False,
				"data": None,
				"error": "No metadata found"
			})
	return {"results": results}
