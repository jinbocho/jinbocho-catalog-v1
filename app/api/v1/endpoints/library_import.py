from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
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
)
from app.infrastructure.database.session import get_db

router = APIRouter(tags=["import"])


@router.post(
	"/full",
	response_model=ImportFullLibraryResponse,
	summary="Restore a full library backup",
	description="Restores a backup produced by GET /v1/export/full into the current family. "
	"Run POST /v1/users/import (auth-service) first and pass its user_id_map here. Bibliographic "
	"records are deduplicated by ISBN against what the family already owns; everything else is "
	"inserted as new (merging into an existing library duplicates rooms/bookcases/books rather "
	"than guessing what should be reused). Requires admin role.",
)
async def import_full_library(
	request: ImportFullLibraryRequest,
	payload: dict = Depends(require_role("admin")),  # type: ignore[type-arg]
	db: AsyncSession = Depends(get_db),
	room_repo=Depends(get_room_repository),
	bookcase_repo=Depends(get_bookcase_repository),
	section_repo=Depends(get_section_repository),
	shelf_repo=Depends(get_shelf_repository),
	record_repo=Depends(get_bibliographic_record_repository),
	book_repo=Depends(get_owned_book_repository),
	book_read_repo=Depends(get_book_read_repository),
	book_loan_repo=Depends(get_book_loan_repository),
	book_history_repo=Depends(get_book_history_repository),
):  # type: ignore[no-untyped-def]
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
	)

	try:
		result = await use_case.execute(
			ImportFullLibraryInput(
				family_id=UUID(payload["family_id"]),
				user_id_map={UUID(k): UUID(v) for k, v in request.user_id_map.items()},
				rooms=[ImportRoomItem(**r.model_dump()) for r in request.rooms],
				bookcases=[ImportBookcaseItem(**b.model_dump()) for b in request.bookcases],
				sections=[ImportSectionItem(**s.model_dump()) for s in request.sections],
				shelves=[ImportShelfItem(**s.model_dump()) for s in request.shelves],
				bibliographic_records=[ImportRecordItem(**r.model_dump()) for r in request.bibliographic_records],
				owned_books=[ImportOwnedBookItem(**b.model_dump()) for b in request.owned_books],
				book_reads=[ImportBookReadItem(**r.model_dump()) for r in request.book_reads],
				book_loans=[ImportBookLoanItem(**loan.model_dump()) for loan in request.book_loans],
				book_history=[ImportBookHistoryItem(**h.model_dump()) for h in request.book_history],
			)
		)
		await db.commit()
	except ValueError as exc:
		await db.rollback()
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

	return ImportFullLibraryResponse(**result.__dict__)
