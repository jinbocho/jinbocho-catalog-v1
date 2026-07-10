from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_book_history_repository, get_current_user_payload
from app.application.use_cases import GetLibraryActivityUseCase
from app.domain.entities import BookHistory
from app.domain.repositories import BookHistoryRepository

router = APIRouter()


@router.get("", summary="Recent library activity for the dashboard feed")
async def get_library_activity(
	limit: int = Query(default=20, ge=1, le=50),
	payload: dict[str, Any] = Depends(get_current_user_payload),
	history_repo: BookHistoryRepository = Depends(get_book_history_repository),
) -> list[BookHistory]:
	return await GetLibraryActivityUseCase(history_repo).execute(UUID(payload["library_id"]), limit=limit)
