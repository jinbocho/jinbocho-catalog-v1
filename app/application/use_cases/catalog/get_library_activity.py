from uuid import UUID

from app.domain.entities import BookEventType, BookHistory
from app.domain.repositories import BookHistoryRepository

FEED_EVENT_TYPES = [BookEventType.CREATED, BookEventType.POSITION_CHANGED, BookEventType.READING_STATUS_CHANGED]


class GetLibraryActivityUseCase:
	"""Recent book-related events for the dashboard activity feed. Deliberately
	excludes metadata_updated (noisy, mostly typo fixes) and deleted (can read
	as accusatory in a shared-household feed) — see FEED_EVENT_TYPES."""

	def __init__(self, history_repo: BookHistoryRepository) -> None:
		self._history_repo = history_repo

	async def execute(self, library_id: UUID, limit: int = 20) -> list[BookHistory]:
		return await self._history_repo.find_recent_by_library(library_id, FEED_EVENT_TYPES, limit=limit)
