from fastapi import APIRouter

from app.api.v1.endpoints import (
	account,
	activity,
	bookcases,
	books,
	export,
	goodreads_import,
	ingestion,
	library_import,
	map,
	members,
	ratings,
	records,
	rooms,
	sections,
	shelf_scan,
	shelves,
	wishlist,
)
from app.api.v1.endpoints.ratings import library_router as ratings_library_router

router = APIRouter()
router.include_router(rooms.router, prefix="/rooms")
router.include_router(bookcases.router, prefix="/bookcases")
router.include_router(sections.router, prefix="/sections")
router.include_router(shelves.router, prefix="/shelves")
router.include_router(records.router, prefix="/bibliographic-records")
router.include_router(books.router, prefix="/books")
router.include_router(ratings.router, prefix="/books")
router.include_router(ratings_library_router, prefix="/ratings")
router.include_router(ingestion.router, prefix="/ingestion")
router.include_router(shelf_scan.router, prefix="/ingestion")
router.include_router(export.router, prefix="/export")
router.include_router(library_import.router, prefix="/import")
router.include_router(goodreads_import.router, prefix="/import")
router.include_router(map.router, prefix="/map")
router.include_router(members.router, prefix="/members")
router.include_router(account.router, prefix="/account")
router.include_router(wishlist.router, prefix="/wishlist")
router.include_router(activity.router, prefix="/activity")

