from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
	get_bibliographic_record_repository,
	get_book_history_repository,
	get_bookcase_repository,
	get_owned_book_repository,
	get_removed_member_repository,
	get_room_repository,
	require_role,
)
from app.api.v1.schemas.export_schemas import DeleteFamilyDataResponse
from app.application.use_cases import DeleteFamilyDataUseCase
from app.domain.repositories import (
	BibliographicRecordRepository,
	BookcaseRepository,
	BookHistoryRepository,
	OwnedBookRepository,
	RemovedMemberRepository,
	RoomRepository,
)
from app.infrastructure.database.session import get_db

router = APIRouter(tags=["account"])


@router.delete(
	"/",
	response_model=DeleteFamilyDataResponse,
	summary="Permanently delete every row this service holds for the family",
	description="Catalog-service half of full account deletion: rooms, bookcases, sections, "
	"shelves, bibliographic records, owned books, reads, loans, history and removed-member "
	"snapshots — everything except the global ISBN lookup cache. Irreversible. The frontend "
	"must call this BEFORE auth-service's DELETE /v1/families/{family_id}: if that ran first, "
	"a failure here would leave this data permanently orphaned with no account left to reach it. "
	"Requires admin role.",
)
async def delete_account_data(
	payload: dict[str, Any] = Depends(require_role("admin")),
	db: AsyncSession = Depends(get_db),
	room_repo: RoomRepository = Depends(get_room_repository),
	bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	book_history_repo: BookHistoryRepository = Depends(get_book_history_repository),
	removed_member_repo: RemovedMemberRepository = Depends(get_removed_member_repository),
) -> DeleteFamilyDataResponse:
	use_case = DeleteFamilyDataUseCase(
		room_repo=room_repo,
		bookcase_repo=bookcase_repo,
		record_repo=record_repo,
		book_repo=book_repo,
		book_history_repo=book_history_repo,
		removed_member_repo=removed_member_repo,
	)
	result = await use_case.execute(UUID(payload["family_id"]))
	await db.commit()
	return DeleteFamilyDataResponse(**result.__dict__)
