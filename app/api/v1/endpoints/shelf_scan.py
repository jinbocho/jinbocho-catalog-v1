from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
	get_bibliographic_record_repository,
	get_book_history_repository,
	get_book_read_repository,
	get_book_search_provider,
	get_bookcase_repository,
	get_duplicate_judge,
	get_fuzzy_dedup_config,
	get_owned_book_repository,
	get_section_repository,
	get_shelf_repository,
	get_shelf_spine_reader,
	require_role,
)
from app.api.v1.schemas.shelf_scan_schemas import (
	AuditBookResponse,
	AuditUnexpectedResponse,
	ShelfAuditRequest,
	ShelfAuditResponse,
	ShelfScanCandidateResponse,
	ShelfScanConfirmRequest,
	ShelfScanConfirmResponse,
	ShelfScanRequest,
	ShelfScanResponse,
)
from app.application.use_cases import (
	AddBookUseCase,
	AuditBook,
	AuditShelfInput,
	AuditShelfUseCase,
	ConfirmShelfScanInput,
	ConfirmShelfScanItem,
	ConfirmShelfScanUseCase,
	FuzzyDedupConfig,
	ScanShelfInput,
	ScanShelfUseCase,
)
from app.domain.repositories import (
	BibliographicRecordRepository,
	BookcaseRepository,
	BookHistoryRepository,
	BookReadRepository,
	BookSearchProvider,
	DuplicateJudge,
	OwnedBookRepository,
	SectionRepository,
	ShelfRepository,
)
from app.domain.repositories.shelf_spine_reader import ShelfSpineReader
from app.infrastructure.database.session import get_db
from app.limiter import limiter

router = APIRouter(tags=["shelf-scan"])


@router.post(
	"/shelf-scan",
	response_model=ShelfScanResponse,
	summary="Scan a shelf photo into a cataloging preview",
	description="Reads book spines from a shelf photo via the AI service, matches each against "
	"the free metadata providers and returns a preview to review — nothing is created until "
	"POST /shelf-scan/confirm. Costs one vision LLM call per photo (ADR-010).",
)
@limiter.limit("10/minute")
async def scan_shelf(
	body: ShelfScanRequest,
	request: Request,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	shelf_repo: ShelfRepository = Depends(get_shelf_repository),
	section_repo: SectionRepository = Depends(get_section_repository),
	bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
	spine_reader: ShelfSpineReader = Depends(get_shelf_spine_reader),
	search_provider: BookSearchProvider = Depends(get_book_search_provider),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
) -> ShelfScanResponse:
	result = await ScanShelfUseCase(
		shelf_repo, section_repo, bookcase_repo, spine_reader, search_provider, record_repo, book_repo
	).execute(
		ScanShelfInput(
			family_id=UUID(payload["family_id"]),
			shelf_id=body.shelf_id,
			image_base64=body.image_base64,
			media_type=body.media_type,
		)
	)
	return ShelfScanResponse(
		available=result.available,
		candidates=[
			ShelfScanCandidateResponse(
				spine_title=c.spine_title,
				spine_author=c.spine_author,
				position=c.position,
				status=c.status,
				already_owned=c.already_owned,
				metadata=c.metadata,
			)
			for c in result.candidates
		],
	)


@router.post(
	"/shelf-scan/confirm",
	response_model=ShelfScanConfirmResponse,
	summary="Create the books confirmed from a shelf scan",
	description="Bulk-creates the reviewed books on the scanned shelf, positioned progressively "
	"after any book already there, in a single transaction. Already-owned duplicates are skipped "
	"per item (reported in skipped_titles) unless flagged as intentional.",
)
@limiter.limit("10/minute")
async def confirm_shelf_scan(
	body: ShelfScanConfirmRequest,
	request: Request,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	db: AsyncSession = Depends(get_db),
	shelf_repo: ShelfRepository = Depends(get_shelf_repository),
	section_repo: SectionRepository = Depends(get_section_repository),
	bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	history_repo: BookHistoryRepository = Depends(get_book_history_repository),
	read_repo: BookReadRepository = Depends(get_book_read_repository),
	dedup_judge: DuplicateJudge = Depends(get_duplicate_judge),
	fuzzy_config: FuzzyDedupConfig = Depends(get_fuzzy_dedup_config),
) -> ShelfScanConfirmResponse:
	add_book = AddBookUseCase(record_repo, book_repo, history_repo, read_repo, dedup_judge, fuzzy_config)
	result = await ConfirmShelfScanUseCase(
		shelf_repo, section_repo, bookcase_repo, book_repo, add_book
	).execute(
		ConfirmShelfScanInput(
			family_id=UUID(payload["family_id"]),
			changed_by=UUID(payload["sub"]),
			shelf_id=body.shelf_id,
			items=[ConfirmShelfScanItem(**item.model_dump()) for item in body.items],
		)
	)
	await db.commit()
	return ShelfScanConfirmResponse(
		created_book_ids=result.created_book_ids,
		skipped_titles=result.skipped_titles,
	)


@router.post(
	"/shelf-scan/audit",
	response_model=ShelfAuditResponse,
	summary="Reconcile a shelf's catalogued books against a fresh photo",
	description="Reads the spines in the photo and diffs them against the books catalogued on this "
	"shelf: present (still here), missing (catalogued but not seen — moved/lent/lost) and unexpected "
	"(seen but not catalogued here). Read-only — creates nothing. One vision LLM call.",
)
@limiter.limit("10/minute")
async def audit_shelf(
	body: ShelfAuditRequest,
	request: Request,
	payload: dict[str, Any] = Depends(require_role("admin", "editor")),
	shelf_repo: ShelfRepository = Depends(get_shelf_repository),
	section_repo: SectionRepository = Depends(get_section_repository),
	bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
	spine_reader: ShelfSpineReader = Depends(get_shelf_spine_reader),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
) -> ShelfAuditResponse:
	result = await AuditShelfUseCase(
		shelf_repo, section_repo, bookcase_repo, spine_reader, book_repo, record_repo
	).execute(
		AuditShelfInput(
			family_id=UUID(payload["family_id"]),
			shelf_id=body.shelf_id,
			image_base64=body.image_base64,
			media_type=body.media_type,
		)
	)
	def _book(b: AuditBook) -> AuditBookResponse:
		return AuditBookResponse(owned_book_id=b.owned_book_id, title=b.title, main_author=b.main_author)

	return ShelfAuditResponse(
		available=result.available,
		present=[_book(b) for b in result.present],
		missing=[_book(b) for b in result.missing],
		unexpected=[
			AuditUnexpectedResponse(title=s.title, author=s.author, position=s.position)
			for s in result.unexpected
		],
	)
