from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database.session import get_db
from app.infrastructure.models import IsbnLookupCacheModel

router = APIRouter()


class IsbnLookupResponse(BaseModel):
    isbn: str
    metadata: dict
    source: str
    cached: bool


class BulkLookupRequest(BaseModel):
    isbns: list[str]


class BulkLookupItem(BaseModel):
    isbn: str
    metadata: dict | None = None
    source: str | None = None
    cached: bool = False
    error: str | None = None


class BulkLookupResponse(BaseModel):
    items: list[BulkLookupItem]


def _normalize_open_library(isbn: str, payload: dict) -> dict:
    authors = [author.get("name") for author in payload.get("authors", []) if author.get("name")]
    publishers = [publisher.get("name") for publisher in payload.get("publishers", []) if publisher.get("name")]
    publish_date = payload.get("publish_date")
    publication_year = None
    if publish_date:
        digits = "".join(ch for ch in publish_date if ch.isdigit())
        if len(digits) >= 4:
            publication_year = int(digits[-4:])
    return {
        "isbn": isbn,
        "title": payload.get("title") or isbn,
        "main_author": authors[0] if authors else None,
        "other_authors": authors[1:] or None,
        "publisher": publishers[0] if publishers else None,
        "publication_year": publication_year,
        "cover_url": payload.get("cover", {}).get("large") or payload.get("cover", {}).get("medium"),
        "raw": payload,
    }


def _normalize_google_books(isbn: str, payload: dict) -> dict:
    volume = payload.get("volumeInfo", {})
    authors = volume.get("authors") or []
    published_date = volume.get("publishedDate")
    publication_year = None
    if published_date:
        digits = "".join(ch for ch in published_date if ch.isdigit())
        if len(digits) >= 4:
            publication_year = int(digits[:4])
    return {
        "isbn": isbn,
        "title": volume.get("title") or isbn,
        "main_author": authors[0] if authors else None,
        "other_authors": authors[1:] or None,
        "publisher": volume.get("publisher"),
        "publication_year": publication_year,
        "language": volume.get("language"),
        "cover_url": (volume.get("imageLinks") or {}).get("thumbnail"),
        "raw": payload,
    }


async def lookup_isbn_metadata(isbn: str, db: AsyncSession) -> tuple[dict, str, bool]:
    now = datetime.utcnow()
    cache_result = await db.execute(select(IsbnLookupCacheModel).where(IsbnLookupCacheModel.isbn == isbn))
    cached = cache_result.scalar_one_or_none()
    if cached and cached.fetched_at >= now - timedelta(days=settings.isbn_cache_ttl_days):
        return cached.metadata, cached.source, True

    async with httpx.AsyncClient(timeout=20.0) as client:
        open_library_response = await client.get(
            f"{settings.open_library_url}/api/books",
            params={
                "bibkeys": f"ISBN:{isbn}",
                "format": "json",
                "jscmd": "data",
            },
        )
        open_library_response.raise_for_status()
        open_library_payload = open_library_response.json().get(f"ISBN:{isbn}")
        if open_library_payload:
            metadata = _normalize_open_library(isbn, open_library_payload)
            source = "open_library"
        else:
            google_response = await client.get(
                f"{settings.google_books_url}/volumes",
                params={"q": f"isbn:{isbn}", "maxResults": 1},
            )
            google_response.raise_for_status()
            items = google_response.json().get("items") or []
            if not items:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Metadata not found for ISBN {isbn}")
            metadata = _normalize_google_books(isbn, items[0])
            source = "google_books"

    if cached:
        cached.metadata = metadata
        cached.source = source
        cached.fetched_at = now
    else:
        db.add(IsbnLookupCacheModel(isbn=isbn, metadata=metadata, source=source, fetched_at=now))
    await db.commit()
    return metadata, source, False


@router.post("/isbn/bulk", response_model=BulkLookupResponse)
async def lookup_bulk_isbn(request: BulkLookupRequest, db: AsyncSession = Depends(get_db)):
    items = []
    for isbn in request.isbns:
        try:
            metadata, source, cached = await lookup_isbn_metadata(isbn, db)
            items.append(BulkLookupItem(isbn=isbn, metadata=metadata, source=source, cached=cached))
        except HTTPException as exc:
            items.append(BulkLookupItem(isbn=isbn, error=exc.detail))
    return BulkLookupResponse(items=items)


@router.post("/isbn/{isbn}", response_model=IsbnLookupResponse)
async def lookup_single_isbn(isbn: str, db: AsyncSession = Depends(get_db)):
    metadata, source, cached = await lookup_isbn_metadata(isbn, db)
    return IsbnLookupResponse(isbn=isbn, metadata=metadata, source=source, cached=cached)
