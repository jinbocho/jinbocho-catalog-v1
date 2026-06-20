from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_removed_member_repository, require_role
from app.api.v1.schemas.export_schemas import RecordRemovedMemberRequest, RemovedMemberExportItem
from app.application.use_cases import RecordRemovedMemberInput, RecordRemovedMemberUseCase
from app.infrastructure.database.session import get_db

router = APIRouter(tags=["members"])


@router.post(
	"/removed",
	response_model=RemovedMemberExportItem,
	summary="Snapshot a family member being removed",
	description="Called by the frontend right before DELETE /v1/users/{id} (auth-service) runs. "
	"auth-service hard-deletes the user row, so this is the last chance to capture their name/email/"
	"role — without it, a future export/import has no way to recreate this person's account; their "
	"owner_id/current_reader_id/etc. references would just be left unresolved. Requires admin role.",
)
async def record_removed_member(
	request: RecordRemovedMemberRequest,
	payload: dict = Depends(require_role("admin")),  # type: ignore[type-arg]
	db: AsyncSession = Depends(get_db),
	removed_member_repo=Depends(get_removed_member_repository),
):  # type: ignore[no-untyped-def]
	use_case = RecordRemovedMemberUseCase(removed_member_repo)
	result = await use_case.execute(
		RecordRemovedMemberInput(
			family_id=UUID(payload["family_id"]),
			id=request.id,
			full_name=request.full_name,
			email=request.email,
			role=request.role,
		)
	)
	await db.commit()
	return RemovedMemberExportItem(
		id=result.id, full_name=result.full_name, email=result.email, role=result.role, removed_at=result.removed_at,
	)
