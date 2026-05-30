from fastapi import APIRouter

from app.api.v1.endpoints import bookcases, books, export, ingestion, records, rooms, sections, shelves

router = APIRouter()
router.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
router.include_router(bookcases.router, prefix="/bookcases", tags=["bookcases"])
router.include_router(sections.router, prefix="/sections", tags=["sections"])
router.include_router(shelves.router, prefix="/shelves", tags=["shelves"])
router.include_router(records.router, prefix="/bibliographic-records", tags=["bibliographic-records"])
router.include_router(books.router, prefix="/books", tags=["owned-books"])
router.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
router.include_router(export.router, prefix="/export", tags=["export"])
