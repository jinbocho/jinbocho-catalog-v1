from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
	get_bibliographic_record_repository,
	get_book_history_repository,
	get_book_loan_repository,
	get_book_read_repository,
	get_current_user_payload,
	get_duplicate_judge,
	get_fuzzy_dedup_config,
	get_owned_book_repository,
	require_role,
)
from app.api.v1.schemas.book_schemas import (
	BookLoanCreate,
	BookLoanResponse,
	BookReadCreate,
	BookReadResponse,
	BulkDeleteBooksRequest,
	BulkDeleteBooksResponse,
	DuplicateBookConflictResponse,
	OwnedBookCreate,
	OwnedBookResponse,
	OwnedBookUpdate,
)
from app.application.use_cases import (
	AddBookInput,
	AddBookUseCase,
	BulkDeleteBooksInput,
	BulkDeleteBooksUseCase,
	DeleteBookInput,
	DeleteBookUseCase,
	FuzzyDedupConfig,
	GetBookHistoryUseCase,
	GetOwnedBookUseCase,
	LendBookUseCase,
	ListActiveLibraryLoansUseCase,
	ListAllLibraryLoansUseCase,
	ListBookLoansUseCase,
	ListBookReadsUseCase,
	ListLibraryReadsUseCase,
	ListOwnedBooksUseCase,
	MarkBookReadUseCase,
	ReturnBookUseCase,
	UnmarkBookReadUseCase,
	UpdateBookMetadataInput,
	UpdateBookMetadataUseCase,
	UpdateBookPositionInput,
	UpdateBookPositionUseCase,
	UpdateReadingStatusInput,
	UpdateReadingStatusUseCase,
)
from app.domain.entities import BookHistory, BookLoan, BookRead, OwnedBook, ReadingStatus
from app.domain.repositories import (
	BibliographicRecordRepository,
	BookHistoryRepository,
	BookLoanRepository,
	BookReadRepository,
	DuplicateJudge,
	OwnedBookRepository,
)
from app.infrastructure.database.session import get_db

router = APIRouter(tags=["books"])


@router.get("/", response_model=list[OwnedBookResponse], summary="List owned books")
async def list_books(
	limit: int = Query(default=50, ge=1, le=200),
	offset: int = Query(default=0, ge=0),
	payload: dict[str, Any] = Depends(get_current_user_payload),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	read_repo: BookReadRepository = Depends(get_book_read_repository),
) -> list[OwnedBook]:
	return await ListOwnedBooksUseCase(book_repo, read_repo).execute(
		UUID(payload["library_id"]), viewer_id=UUID(payload["sub"]), limit=limit, offset=offset
	)


# Static literal routes must be declared before /{book_id} so FastAPI does not consume
# them as UUID path parameters.
@router.get("/reads", response_model=list[BookReadResponse], summary="List all reads for the library")
async def list_library_reads(
	payload: dict[str, Any] = Depends(get_current_user_payload),
	read_repo: BookReadRepository = Depends(get_book_read_repository),
) -> list[BookRead]:
	return await ListLibraryReadsUseCase(read_repo).execute(UUID(payload["library_id"]))


@router.get("/loans/active", response_model=list[BookLoanResponse], summary="List all active loans for the library")
async def list_active_loans(
	payload: dict[str, Any] = Depends(get_current_user_payload),
	loan_repo: BookLoanRepository = Depends(get_book_loan_repository),
) -> list[BookLoan]:
	return await ListActiveLibraryLoansUseCase(loan_repo).execute(UUID(payload["library_id"]))


@router.get(
	"/loans/all",
	response_model=list[BookLoanResponse],
	summary="List all loans for the library, active and returned",
)
async def list_all_loans(
	payload: dict[str, Any] = Depends(get_current_user_payload),
	loan_repo: BookLoanRepository = Depends(get_book_loan_repository),
) -> list[BookLoan]:
	return await ListAllLibraryLoansUseCase(loan_repo).execute(UUID(payload["library_id"]))


@router.post(
	"/",
	response_model=OwnedBookResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Add book",
	responses={
		409: {
			"description": "Looks like a duplicate of a book already owned by the same owner. "
			"Resubmit with is_intentional_duplicate=true to add it anyway.",
			"model": DuplicateBookConflictResponse,
		},
	},
)
async def add_book(
	request: OwnedBookCreate,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
	history_repo: BookHistoryRepository = Depends(get_book_history_repository),
	read_repo: BookReadRepository = Depends(get_book_read_repository),
	dedup_judge: DuplicateJudge = Depends(get_duplicate_judge),
	fuzzy_config: FuzzyDedupConfig = Depends(get_fuzzy_dedup_config),
) -> OwnedBook:
	# DuplicateBookError propagates to the global handler in
	# app/core/exception_handlers.py (same pattern as LookupError/ValueError
	# elsewhere); get_db() rolls back automatically when an exception escapes.
	book = await AddBookUseCase(record_repo, book_repo, history_repo, read_repo, dedup_judge, fuzzy_config).execute(
		AddBookInput(library_id=UUID(payload["library_id"]), changed_by=UUID(payload["sub"]), **request.model_dump())
	)
	await db.commit()
	return book


@router.post(
	"/bulk-delete",
	response_model=BulkDeleteBooksResponse,
	summary="Bulk-delete books",
	responses={
		404: {"description": "One or more book IDs were not found — nothing was deleted."},
		403: {"description": "One or more book IDs belong to another library — nothing was deleted."},
	},
)
async def bulk_delete_books(
	request: BulkDeleteBooksRequest,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	history_repo: BookHistoryRepository = Depends(get_book_history_repository),
) -> BulkDeleteBooksResponse:
	deleted = await BulkDeleteBooksUseCase(book_repo, history_repo).execute(
		BulkDeleteBooksInput(
			book_ids=request.book_ids, library_id=UUID(payload["library_id"]), changed_by=UUID(payload["sub"])
		)
	)
	await db.commit()
	return BulkDeleteBooksResponse(deleted=deleted)


@router.get("/{book_id}", response_model=OwnedBookResponse, summary="Get book")
async def get_book(
	book_id: UUID,
	payload: dict[str, Any] = Depends(get_current_user_payload),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
	read_repo: BookReadRepository = Depends(get_book_read_repository),
) -> OwnedBook:
	result = await GetOwnedBookUseCase(book_repo, record_repo, read_repo).execute(
		book_id, UUID(payload["library_id"]), viewer_id=UUID(payload["sub"])
	)
	return result.book


@router.patch("/{book_id}", response_model=OwnedBookResponse, summary="Update book metadata")
async def update_book(
	book_id: UUID,
	request: OwnedBookUpdate,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	history_repo: BookHistoryRepository = Depends(get_book_history_repository),
	read_repo: BookReadRepository = Depends(get_book_read_repository),
) -> OwnedBook:
	updated = await UpdateBookMetadataUseCase(book_repo, read_repo, history_repo).execute(
		UpdateBookMetadataInput(
			book_id=book_id,
			library_id=UUID(payload["library_id"]),
			changed_by=UUID(payload["sub"]),
			**request.model_dump(exclude_unset=True),
		)
	)
	await db.commit()
	return updated


@router.post("/{book_id}/position", response_model=OwnedBookResponse, summary="Update book position")
async def update_book_position(
	book_id: UUID,
	room_id: UUID | None = None,
	bookcase_id: UUID | None = None,
	section_id: UUID | None = None,
	shelf_id: UUID | None = None,
	shelf_position: int | None = None,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	history_repo: BookHistoryRepository = Depends(get_book_history_repository),
) -> OwnedBook:
	updated = await UpdateBookPositionUseCase(book_repo, history_repo).execute(
		UpdateBookPositionInput(
			book_id=book_id,
			library_id=UUID(payload["library_id"]),
			changed_by=UUID(payload["sub"]),
			room_id=room_id,
			bookcase_id=bookcase_id,
			section_id=section_id,
			shelf_id=shelf_id,
			shelf_position=shelf_position,
			position_description=None,
		)
	)
	await db.commit()
	return updated


@router.post("/{book_id}/reading-status", response_model=OwnedBookResponse, summary="Update reading status")
async def update_reading_status(
	book_id: UUID,
	reading_status: ReadingStatus,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	history_repo: BookHistoryRepository = Depends(get_book_history_repository),
	read_repo: BookReadRepository = Depends(get_book_read_repository),
) -> OwnedBook:
	updated = await UpdateReadingStatusUseCase(book_repo, read_repo, history_repo).execute(
		UpdateReadingStatusInput(
			book_id=book_id,
			library_id=UUID(payload["library_id"]),
			changed_by=UUID(payload["sub"]),
			reading_status=reading_status,
		)
	)
	await db.commit()
	return updated


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete book")
async def delete_book(
	book_id: UUID,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	history_repo: BookHistoryRepository = Depends(get_book_history_repository),
) -> None:
	await DeleteBookUseCase(book_repo, history_repo).execute(
		DeleteBookInput(book_id=book_id, library_id=UUID(payload["library_id"]), changed_by=UUID(payload["sub"]))
	)
	await db.commit()


@router.get("/{book_id}/history", summary="Get book history")
async def get_book_history(
	book_id: UUID,
	payload: dict[str, Any] = Depends(get_current_user_payload),
	history_repo: BookHistoryRepository = Depends(get_book_history_repository),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
) -> list[BookHistory]:
	return await GetBookHistoryUseCase(history_repo, book_repo).execute(book_id, UUID(payload["library_id"]))


@router.get("/{book_id}/reads", response_model=list[BookReadResponse], summary="List readers of a book")
async def list_book_reads(
	book_id: UUID,
	payload: dict[str, Any] = Depends(get_current_user_payload),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	read_repo: BookReadRepository = Depends(get_book_read_repository),
) -> list[BookRead]:
	return await ListBookReadsUseCase(book_repo, read_repo).execute(book_id, UUID(payload["library_id"]))


@router.post(
	"/{book_id}/reads",
	response_model=BookReadResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Mark book as read by a member",
)
async def mark_book_read(
	book_id: UUID,
	request: BookReadCreate,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	read_repo: BookReadRepository = Depends(get_book_read_repository),
) -> BookRead:
	result = await MarkBookReadUseCase(book_repo, read_repo).execute(
		book_id, UUID(payload["library_id"]), request.user_id, request.read_at
	)
	await db.commit()
	return result


@router.delete(
	"/{book_id}/reads/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove read mark for a member"
)
async def unmark_book_read(
	book_id: UUID,
	user_id: UUID,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	read_repo: BookReadRepository = Depends(get_book_read_repository),
) -> None:
	await UnmarkBookReadUseCase(book_repo, read_repo).execute(book_id, UUID(payload["library_id"]), user_id)
	await db.commit()


@router.get("/{book_id}/loans", response_model=list[BookLoanResponse], summary="List loan history for a book")
async def list_book_loans(
	book_id: UUID,
	payload: dict[str, Any] = Depends(get_current_user_payload),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	loan_repo: BookLoanRepository = Depends(get_book_loan_repository),
) -> list[BookLoan]:
	return await ListBookLoansUseCase(book_repo, loan_repo).execute(book_id, UUID(payload["library_id"]))


@router.post(
	"/{book_id}/loans",
	response_model=BookLoanResponse,
	status_code=status.HTTP_201_CREATED,
	summary="Lend a book to someone outside the library",
)
async def lend_book(
	book_id: UUID,
	request: BookLoanCreate,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	loan_repo: BookLoanRepository = Depends(get_book_loan_repository),
) -> BookLoan:
	result = await LendBookUseCase(book_repo, loan_repo).execute(
		book_id, UUID(payload["library_id"]), request.borrower_name, request.due_date, request.borrower_user_id,
	)
	await db.commit()
	return result


@router.post("/{book_id}/loans/return", response_model=BookLoanResponse, summary="Mark the active loan as returned")
async def return_book(
	book_id: UUID,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	loan_repo: BookLoanRepository = Depends(get_book_loan_repository),
) -> BookLoan:
	returned_loan = await ReturnBookUseCase(book_repo, loan_repo).execute(book_id, UUID(payload["library_id"]))
	await db.commit()
	return returned_loan
