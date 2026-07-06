from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
	get_bibliographic_record_repository,
	get_book_history_repository,
	get_book_loan_repository,
	get_book_read_repository,
	get_bookcase_repository,
	get_owned_book_repository,
	get_room_repository,
	get_section_repository,
	get_shelf_repository,
	get_wishlist_repository,
	require_role,
)
from app.api.v1.schemas.export_schemas import ImportFullLibraryRequest, ImportFullLibraryResponse
from app.application.use_cases import (
	ImportBookcaseItem,
	ImportBookHistoryItem,
	ImportBookLoanItem,
	ImportBookReadItem,
	ImportFullLibraryInput,
	ImportFullLibraryUseCase,
	ImportOwnedBookItem,
	ImportRecordItem,
	ImportRoomItem,
	ImportSectionItem,
	ImportShelfItem,
	ImportWishlistItem,
)
from app.domain.repositories import (
	BibliographicRecordRepository,
	BookcaseRepository,
	BookHistoryRepository,
	BookLoanRepository,
	BookReadRepository,
	OwnedBookRepository,
	RoomRepository,
	SectionRepository,
	ShelfRepository,
	WishlistRepository,
)
from app.infrastructure.database.session import get_db
from app.limiter import limiter

router = APIRouter(tags=["import"])


@router.post(
	"/full",
	response_model=ImportFullLibraryResponse,
	summary="Restore a full library backup",
	description="Restores a backup produced by GET /v1/export/full into the current library. "
	"Run POST /v1/users/import (auth-service) first and pass its user_id_map here. Bibliographic "
	"records are deduplicated by ISBN against what the library already owns; everything else is "
	"inserted as new (merging into an existing library duplicates rooms/bookcases/books rather "
	"than guessing what should be reused). Requires admin role.",
)
@limiter.limit("3/minute")
async def import_full_library(
	body: ImportFullLibraryRequest,
	request: Request,
	payload: dict[str, Any] = Depends(require_role("admin")),
	db: AsyncSession = Depends(get_db),
	room_repo: RoomRepository = Depends(get_room_repository),
	bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
	section_repo: SectionRepository = Depends(get_section_repository),
	shelf_repo: ShelfRepository = Depends(get_shelf_repository),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	book_read_repo: BookReadRepository = Depends(get_book_read_repository),
	book_loan_repo: BookLoanRepository = Depends(get_book_loan_repository),
	book_history_repo: BookHistoryRepository = Depends(get_book_history_repository),
	wishlist_repo: WishlistRepository = Depends(get_wishlist_repository),
) -> ImportFullLibraryResponse:
	use_case = ImportFullLibraryUseCase(
		room_repo=room_repo,
		bookcase_repo=bookcase_repo,
		section_repo=section_repo,
		shelf_repo=shelf_repo,
		record_repo=record_repo,
		book_repo=book_repo,
		book_read_repo=book_read_repo,
		book_loan_repo=book_loan_repo,
		book_history_repo=book_history_repo,
		wishlist_repo=wishlist_repo,
	)

	# ValueError propagates to the global handler in app/core/exception_handlers.py
	# (409, same as every other use case); get_db() rolls back automatically when
	# an exception escapes.
	result = await use_case.execute(
		ImportFullLibraryInput(
			library_id=UUID(payload["library_id"]),
			user_id_map={UUID(k): UUID(v) for k, v in body.user_id_map.items()},
			rooms=[ImportRoomItem(**r.model_dump()) for r in body.rooms],
			bookcases=[ImportBookcaseItem(**b.model_dump()) for b in body.bookcases],
			sections=[ImportSectionItem(**s.model_dump()) for s in body.sections],
			shelves=[ImportShelfItem(**s.model_dump()) for s in body.shelves],
			bibliographic_records=[ImportRecordItem(**r.model_dump()) for r in body.bibliographic_records],
			owned_books=[ImportOwnedBookItem(**b.model_dump()) for b in body.owned_books],
			book_reads=[ImportBookReadItem(**r.model_dump()) for r in body.book_reads],
			book_loans=[ImportBookLoanItem(**loan.model_dump()) for loan in body.book_loans],
			book_history=[ImportBookHistoryItem(**h.model_dump()) for h in body.book_history],
			wishlist_items=[ImportWishlistItem(**w.model_dump()) for w in body.wishlist_items],
		)
	)
	await db.commit()

	return ImportFullLibraryResponse(**result.__dict__)
