from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
	get_bibliographic_record_repository,
	get_book_history_repository,
	get_book_rating_repository,
	get_book_read_repository,
	get_duplicate_judge,
	get_fuzzy_dedup_config,
	get_owned_book_repository,
	require_role,
)
from app.api.v1.schemas.goodreads_schemas import (
	GoodreadsConfirmRequest,
	GoodreadsConfirmResponse,
	GoodreadsPreviewRequest,
	GoodreadsPreviewResponse,
	GoodreadsPreviewRowResponse,
	GoodreadsSkippedItemResponse,
)
from app.application.use_cases import (
	AddBookUseCase,
	ConfirmGoodreadsImportInput,
	ConfirmGoodreadsImportItem,
	ConfirmGoodreadsImportUseCase,
	FuzzyDedupConfig,
	PreviewGoodreadsImportInput,
	PreviewGoodreadsImportUseCase,
)
from app.domain.repositories import (
	BibliographicRecordRepository,
	BookHistoryRepository,
	BookRatingRepository,
	BookReadRepository,
	DuplicateJudge,
	OwnedBookRepository,
)
from app.infrastructure.database.session import get_db
from app.limiter import limiter

router = APIRouter(tags=["goodreads-import"])


@router.post(
	"/goodreads/preview",
	response_model=GoodreadsPreviewResponse,
	summary="Parse a Goodreads export CSV into an import preview",
	description="Parses the CSV and classifies each row (new / already_owned / invalid) against what the "
	"library already owns — nothing is created until POST /import/goodreads/confirm.",
)
@limiter.limit("3/minute")
async def preview_goodreads_import(
	body: GoodreadsPreviewRequest,
	request: Request,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
) -> GoodreadsPreviewResponse:
	result = await PreviewGoodreadsImportUseCase(record_repo, book_repo).execute(
		PreviewGoodreadsImportInput(library_id=UUID(payload["library_id"]), csv_text=body.csv_text)
	)
	return GoodreadsPreviewResponse(
		rows=[
			GoodreadsPreviewRowResponse(
				row_number=r.row_number,
				status=r.status,
				title=r.title,
				main_author=r.main_author,
				other_authors=r.other_authors,
				isbn=r.isbn,
				publisher=r.publisher,
				publication_year=r.publication_year,
				reading_status=r.reading_status,
				rating=r.rating,
				review=r.review,
				read_at=r.read_at,
				tags=r.tags,
			)
			for r in result.rows
		]
	)


@router.post(
	"/goodreads/confirm",
	response_model=GoodreadsConfirmResponse,
	summary="Create the books confirmed from a Goodreads import preview",
	description="Bulk-creates the reviewed books with no physical position (Goodreads has no location "
	"model) — the user places them later. Already-owned duplicates and rows matched twice in the same "
	"CSV are skipped per item (reported in `skipped`, with why) unless flagged as intentional. "
	"My Rating and Date Read are attached to the importing user.",
)
@limiter.limit("3/minute")
async def confirm_goodreads_import(
	body: GoodreadsConfirmRequest,
	request: Request,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	history_repo: BookHistoryRepository = Depends(get_book_history_repository),
	read_repo: BookReadRepository = Depends(get_book_read_repository),
	rating_repo: BookRatingRepository = Depends(get_book_rating_repository),
	dedup_judge: DuplicateJudge = Depends(get_duplicate_judge),
	fuzzy_config: FuzzyDedupConfig = Depends(get_fuzzy_dedup_config),
) -> GoodreadsConfirmResponse:
	add_book = AddBookUseCase(record_repo, book_repo, history_repo, read_repo, dedup_judge, fuzzy_config)
	result = await ConfirmGoodreadsImportUseCase(add_book, read_repo, rating_repo).execute(
		ConfirmGoodreadsImportInput(
			library_id=UUID(payload["library_id"]),
			changed_by=UUID(payload["sub"]),
			items=[ConfirmGoodreadsImportItem(**item.model_dump()) for item in body.items],
		)
	)
	await db.commit()
	return GoodreadsConfirmResponse(
		created_book_ids=result.created_book_ids,
		skipped=[
			GoodreadsSkippedItemResponse(title=s.title, reason=s.reason, row_number=s.row_number)
			for s in result.skipped
		],
		rated_count=result.rated_count,
		read_count=result.read_count,
	)
